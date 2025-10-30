# Integration State Machine

**Version:** 1.0
**Date:** 2025-10-30
**Sprint:** 2 - MCP Integration Framework
**Author:** System Architect

---

## Table of Contents

1. [Overview](#overview)
2. [State Definitions](#state-definitions)
3. [State Transitions](#state-transitions)
4. [Transition Rules](#transition-rules)
5. [Error Recovery Flows](#error-recovery-flows)
6. [Implementation](#implementation)
7. [Monitoring](#monitoring)

---

## Overview

The Integration State Machine manages the complete lifecycle of MCP integrations from initial connection through active operation, error states, and eventual disconnection. This state machine ensures consistent, predictable behavior across all 13 platform integrations.

### Design Goals
- **Deterministic**: Same inputs always produce same state transitions
- **Observable**: All state changes logged to event sourcing system
- **Recoverable**: Clear paths from error states back to healthy operation
- **Auditable**: Complete history of state changes for compliance

---

## State Definitions

### State Enumeration
```python
class IntegrationState(str, Enum):
    # Initial States
    PENDING = "pending"          # Created but not yet authorized
    AUTHORIZING = "authorizing"  # OAuth flow in progress

    # Active States
    CONNECTED = "connected"      # OAuth completed, tokens stored
    ACTIVE = "active"           # Fully operational and syncing

    # Degraded States
    ERROR = "error"             # Temporary error, automatic retry
    DEGRADED = "degraded"       # Partial functionality only

    # Terminal States
    REVOKED = "revoked"         # User disconnected
    EXPIRED = "expired"         # Token expired, needs reauth
    DELETED = "deleted"         # Soft deleted (tombstone)
```

### State Descriptions

#### PENDING
**Description:** Integration has been created but not yet authorized

**Characteristics:**
- No OAuth tokens stored
- User has not completed authorization
- Awaiting user action
- No data sync occurring

**Database Values:**
```sql
status = 'pending'
health_status = 'unknown'
connected_at = NULL
credentials_enc = NULL
```

**Valid Actions:**
- Initiate OAuth flow → AUTHORIZING
- Delete integration → DELETED

---

#### AUTHORIZING
**Description:** OAuth flow is in progress

**Characteristics:**
- User has clicked "Connect" button
- Redirected to OAuth provider
- Awaiting callback with auth code
- Time-limited state (10 minute timeout)

**Database Values:**
```sql
status = 'authorizing'
health_status = 'unknown'
metadata->>'oauth_state' = '<state_token>'
```

**Valid Actions:**
- OAuth success → CONNECTED
- OAuth failure → ERROR or PENDING
- Timeout → PENDING

---

#### CONNECTED
**Description:** OAuth completed successfully, tokens stored

**Characteristics:**
- Access token and refresh token encrypted and stored
- Initial health check passed
- Ready to begin data sync
- Not yet actively syncing

**Database Values:**
```sql
status = 'connected'
health_status = 'healthy'
connected_at = now()
credentials_enc = <encrypted_tokens>
consecutive_failures = 0
```

**Valid Actions:**
- Begin sync → ACTIVE
- Health check failure → ERROR
- Token expiration → EXPIRED
- User disconnect → REVOKED

---

#### ACTIVE
**Description:** Fully operational and actively syncing data

**Characteristics:**
- Data sync jobs running
- Webhooks (if supported) receiving events
- Health checks passing
- Tokens being refreshed automatically

**Database Values:**
```sql
status = 'active'
health_status = 'healthy'
last_sync_at = now()
consecutive_failures = 0
circuit_breaker_state = 'closed'
```

**Valid Actions:**
- Health check failure → DEGRADED or ERROR
- API errors → ERROR
- Rate limit exceeded → DEGRADED
- Token expiration → EXPIRED
- User disconnect → REVOKED

---

#### ERROR
**Description:** Temporary error state with automatic recovery

**Characteristics:**
- Recoverable error occurred
- Automatic retry scheduled
- Circuit breaker may be open
- Data sync paused

**Database Values:**
```sql
status = 'error'
health_status = 'unhealthy'
error_message = '<error_description>'
consecutive_failures = 1-5
circuit_breaker_state = 'open' (if >= 5 failures)
```

**Valid Actions:**
- Retry success → CONNECTED or ACTIVE
- Continued failures → remains ERROR (max 3 retries)
- Manual reauthorization → PENDING
- User disconnect → REVOKED

---

#### DEGRADED
**Description:** Partial functionality only

**Characteristics:**
- Some features working, others not
- Typically due to rate limiting
- Automatic recovery expected
- Limited data sync continuing

**Database Values:**
```sql
status = 'connected' (or 'active')
health_status = 'degraded'
metadata->>'degraded_reason' = 'rate_limit'
```

**Valid Actions:**
- Full recovery → ACTIVE
- Worsening issues → ERROR
- User disconnect → REVOKED

---

#### REVOKED
**Description:** User explicitly disconnected the integration

**Characteristics:**
- OAuth tokens revoked with provider
- Credentials removed from database
- Cannot automatically recover
- Requires new authorization

**Database Values:**
```sql
status = 'revoked'
health_status = 'unknown'
credentials_enc = NULL
metadata->>'revoked_at' = now()
metadata->>'revoked_by' = '<user_id>'
```

**Valid Actions:**
- Reconnect → PENDING
- Delete → DELETED

---

#### EXPIRED
**Description:** OAuth tokens expired, needs reauthorization

**Characteristics:**
- Access token expired
- Refresh token also expired or invalid
- Automatic refresh failed
- User intervention required

**Database Values:**
```sql
status = 'expired'
health_status = 'unknown'
error_message = 'Token expired, reauthorization required'
metadata->>'token_expired_at' = now()
```

**Valid Actions:**
- Reauthorize → PENDING → CONNECTED
- Delete → DELETED

---

#### DELETED
**Description:** Integration soft-deleted (tombstone record)

**Characteristics:**
- Terminal state (no transitions out)
- Credentials purged
- Audit trail preserved
- Cannot be recovered

**Database Values:**
```sql
status = 'deleted'
credentials_enc = NULL
deleted_at = now()
```

**Valid Actions:**
- None (terminal state)

---

## State Transitions

### State Transition Diagram

```
                          ┌──────────┐
                          │ PENDING  │
                          └────┬─────┘
                               │
                               │ initiate_oauth()
                               ▼
                         ┌────────────┐
                         │AUTHORIZING │
                         └─────┬──────┘
                               │
                    ┌──────────┴──────────┐
                    │ oauth_success()     │ oauth_failure()
                    ▼                     ▼
              ┌──────────┐           ┌─────────┐
              │CONNECTED │           │  ERROR  │
              └────┬─────┘           └────┬────┘
                   │                      │
                   │ start_sync()         │ retry_success()
                   ▼                      │
              ┌─────────┐                 │
         ┌────│ ACTIVE  │◄────────────────┘
         │    └────┬────┘
         │         │
         │         │ health_check_fail()
         │         ▼
         │    ┌──────────┐
         │    │ DEGRADED │
         │    └────┬─────┘
         │         │
         │         │ severe_failure()
         │         ▼
         │    ┌─────────┐
         └───>│  ERROR  │
              └────┬────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        │ disconnect()        │ token_expired()
        ▼          │          ▼
   ┌─────────┐     │     ┌─────────┐
   │ REVOKED │     │     │ EXPIRED │
   └────┬────┘     │     └────┬────┘
        │          │          │
        │          │          │ reconnect()
        │          │          ▼
        │          │     ┌──────────┐
        │          │     │ PENDING  │
        │          │     └──────────┘
        │          │
        │          │ delete()
        │          ▼
        │     ┌─────────┐
        └────>│ DELETED │
              └─────────┘
                (terminal)
```

### Transition Table

| From State  | To State   | Trigger                | Condition                      |
|-------------|------------|------------------------|--------------------------------|
| PENDING     | AUTHORIZING| initiate_oauth()       | User clicks "Connect"          |
| PENDING     | DELETED    | delete()               | User deletes integration       |
| AUTHORIZING | CONNECTED  | oauth_success()        | OAuth callback successful      |
| AUTHORIZING | ERROR      | oauth_failure()        | OAuth callback failed          |
| AUTHORIZING | PENDING    | timeout()              | 10 minute timeout expired      |
| CONNECTED   | ACTIVE     | start_sync()           | First sync job started         |
| CONNECTED   | ERROR      | health_check_fail()    | Health check failed            |
| CONNECTED   | EXPIRED    | token_expired()        | Token cannot be refreshed      |
| CONNECTED   | REVOKED    | disconnect()           | User disconnects               |
| ACTIVE      | DEGRADED   | rate_limit()           | Rate limit encountered         |
| ACTIVE      | ERROR      | api_failure()          | API error occurred             |
| ACTIVE      | EXPIRED    | token_expired()        | Token cannot be refreshed      |
| ACTIVE      | REVOKED    | disconnect()           | User disconnects               |
| DEGRADED    | ACTIVE     | recover()              | Full functionality restored    |
| DEGRADED    | ERROR      | severe_failure()       | Errors worsen                  |
| DEGRADED    | REVOKED    | disconnect()           | User disconnects               |
| ERROR       | CONNECTED  | retry_success()        | Retry successful (from CONNECTED state) |
| ERROR       | ACTIVE     | retry_success()        | Retry successful (from ACTIVE state) |
| ERROR       | EXPIRED    | auth_failure()         | Authentication cannot be fixed |
| ERROR       | REVOKED    | disconnect()           | User disconnects               |
| ERROR       | DELETED    | delete()               | User deletes                   |
| REVOKED     | PENDING    | reconnect()            | User initiates reconnection    |
| REVOKED     | DELETED    | delete()               | User deletes                   |
| EXPIRED     | PENDING    | reauthorize()          | User re-authorizes             |
| EXPIRED     | DELETED    | delete()               | User deletes                   |

---

## Transition Rules

### Rule 1: Validation Before Transition
**Requirement:** All state transitions must be validated before execution

```python
def validate_transition(from_state: IntegrationState,
                       to_state: IntegrationState) -> bool:
    """Validate if transition is allowed"""
    allowed_transitions = {
        IntegrationState.PENDING: [
            IntegrationState.AUTHORIZING,
            IntegrationState.DELETED
        ],
        IntegrationState.AUTHORIZING: [
            IntegrationState.CONNECTED,
            IntegrationState.ERROR,
            IntegrationState.PENDING
        ],
        # ... (see full table above)
    }

    if to_state not in allowed_transitions.get(from_state, []):
        raise InvalidStateTransitionError(
            f"Cannot transition from {from_state} to {to_state}"
        )

    return True
```

### Rule 2: Event Logging
**Requirement:** Every state transition must be logged to ops.events

```python
async def transition_state(integration_id: str,
                          to_state: IntegrationState,
                          reason: str = None) -> None:
    """Execute state transition with logging"""

    current = await get_current_state(integration_id)
    validate_transition(current.status, to_state)

    # Update state
    await update_integration_state(integration_id, to_state)

    # Log event
    await log_integration_event(
        workspace_id=current.workspace_id,
        event_type=f"integration.state.{to_state}",
        entity_id=integration_id,
        payload={
            "from_state": current.status,
            "to_state": to_state,
            "reason": reason
        }
    )

    # Trigger side effects
    await handle_state_change(integration_id, current.status, to_state)
```

### Rule 3: Idempotency
**Requirement:** Transitioning to the same state is idempotent (no-op)

```python
async def transition_state(integration_id: str,
                          to_state: IntegrationState) -> None:
    current_state = await get_current_state(integration_id)

    if current_state == to_state:
        # Already in target state, no-op
        return

    # Proceed with transition...
```

### Rule 4: Atomicity
**Requirement:** State transitions must be atomic (succeed or rollback)

```python
async def transition_state(integration_id: str,
                          to_state: IntegrationState) -> None:
    async with db.transaction():
        # All operations within transaction
        await update_state(integration_id, to_state)
        await log_event(...)
        await trigger_side_effects(...)
        # Commits on success, rolls back on error
```

---

## Error Recovery Flows

### Recovery Flow 1: Temporary API Error

```
ACTIVE → ERROR → (auto-retry 3x) → ACTIVE
         ↓
         (if retry exhausted)
         ↓
      EXPIRED (if auth issue)
         or
      ERROR (remains, manual intervention)
```

**Implementation:**
```python
async def handle_api_error(integration_id: str, error: Exception):
    """Handle temporary API errors with retry"""

    # Transition to ERROR
    await transition_state(integration_id, IntegrationState.ERROR,
                          reason=str(error))

    # Schedule retries with exponential backoff
    for attempt in range(3):
        delay = 2 ** attempt  # 1s, 2s, 4s
        await asyncio.sleep(delay)

        try:
            # Attempt recovery
            await test_connection(integration_id)

            # Success - recover to ACTIVE
            await transition_state(integration_id, IntegrationState.ACTIVE,
                                  reason="Auto-recovery successful")
            return

        except Exception as e:
            # Retry failed, continue
            await log_retry_failure(integration_id, attempt, e)

    # All retries exhausted
    # Check if auth error
    if is_auth_error(error):
        await transition_state(integration_id, IntegrationState.EXPIRED,
                              reason="Authentication failed")
    # Otherwise stay in ERROR for manual intervention
```

### Recovery Flow 2: Rate Limit Exceeded

```
ACTIVE → DEGRADED → (wait for rate limit reset) → ACTIVE
```

**Implementation:**
```python
async def handle_rate_limit(integration_id: str, retry_after: int):
    """Handle rate limiting gracefully"""

    # Transition to DEGRADED
    await transition_state(integration_id, IntegrationState.DEGRADED,
                          reason=f"Rate limited, retry after {retry_after}s")

    # Update metadata with retry time
    await update_integration_metadata(integration_id, {
        "degraded_reason": "rate_limit",
        "retry_after": retry_after,
        "degraded_at": datetime.utcnow().isoformat()
    })

    # Schedule recovery
    await schedule_task(
        delay=retry_after,
        task=recover_from_rate_limit,
        args=(integration_id,)
    )


async def recover_from_rate_limit(integration_id: str):
    """Attempt to recover from rate limiting"""

    try:
        # Test connection
        await test_connection(integration_id)

        # Recover to ACTIVE
        await transition_state(integration_id, IntegrationState.ACTIVE,
                              reason="Recovered from rate limit")

    except Exception as e:
        # Still rate limited or other error
        await handle_api_error(integration_id, e)
```

### Recovery Flow 3: Token Expired

```
ACTIVE → EXPIRED → (user re-authorizes) → PENDING → AUTHORIZING → CONNECTED → ACTIVE
```

**Implementation:**
```python
async def handle_token_expiry(integration_id: str):
    """Handle OAuth token expiration"""

    # Try automatic refresh first
    try:
        await refresh_oauth_token(integration_id)
        # Success - no state change needed
        return

    except RefreshTokenExpiredError:
        # Cannot auto-refresh, need reauth
        await transition_state(integration_id, IntegrationState.EXPIRED,
                              reason="OAuth token expired, reauthorization required")

        # Notify user
        integration = await get_integration(integration_id)
        await send_notification(
            workspace_id=integration.workspace_id,
            founder_id=integration.founder_id,
            type="integration_expired",
            message=f"Your {integration.platform} integration needs reauthorization",
            action_url=f"/integrations/reconnect/{integration_id}"
        )
```

### Recovery Flow 4: Circuit Breaker Trip

```
ACTIVE → ERROR (circuit opens) → (5 min timeout) → ERROR (half-open) → test → ACTIVE
                                                                      → test_fails → ERROR (open)
```

**Implementation:**
```python
class CircuitBreakerStateMachine:
    """Nested state machine for circuit breaker"""

    async def handle_failure(self, integration_id: str):
        """Handle integration failure"""

        failures = await increment_failure_count(integration_id)

        if failures >= 5:
            # Open circuit
            await update_circuit_state(integration_id, "open")
            await transition_state(integration_id, IntegrationState.ERROR,
                                  reason="Circuit breaker opened")

            # Schedule recovery attempt
            await schedule_task(
                delay=300,  # 5 minutes
                task=self.attempt_recovery,
                args=(integration_id,)
            )

    async def attempt_recovery(self, integration_id: str):
        """Attempt to close circuit"""

        # Move to half-open
        await update_circuit_state(integration_id, "half_open")

        try:
            # Test connection (single attempt)
            await test_connection(integration_id)

            # Success - close circuit
            await update_circuit_state(integration_id, "closed")
            await reset_failure_count(integration_id)
            await transition_state(integration_id, IntegrationState.ACTIVE,
                                  reason="Circuit breaker closed")

        except Exception as e:
            # Failed - reopen circuit
            await update_circuit_state(integration_id, "open")
            await self.handle_failure(integration_id)
```

---

## Implementation

### Database Schema

State is stored in `core.integrations` table:

```sql
CREATE TABLE core.integrations (
    id                      uuid PRIMARY KEY,
    workspace_id            uuid NOT NULL,
    platform                platform_enum NOT NULL,
    status                  integration_status NOT NULL,  -- The state
    health_status           text,
    consecutive_failures    int DEFAULT 0,
    circuit_breaker_state   text DEFAULT 'closed',
    error_message           text,
    connected_at            timestamptz,
    last_health_check       timestamptz,
    metadata                jsonb
);
```

### State Transition Function

```python
async def transition_integration_state(
    integration_id: str,
    new_state: IntegrationState,
    reason: str = None,
    metadata: dict = None
) -> None:
    """
    Safely transition integration to new state

    Args:
        integration_id: Integration UUID
        new_state: Target state
        reason: Human-readable reason for transition
        metadata: Additional state-specific data

    Raises:
        InvalidStateTransitionError: If transition not allowed
        DatabaseError: If update fails
    """

    async with db.transaction():
        # Get current state
        current = await db.fetchrow("""
            SELECT status, platform, workspace_id, founder_id
            FROM core.integrations
            WHERE id = $1
            FOR UPDATE  -- Lock row
        """, integration_id)

        if not current:
            raise IntegrationNotFoundError(integration_id)

        current_state = IntegrationState(current['status'])

        # Validate transition
        if current_state == new_state:
            return  # Idempotent

        if not StateTransition.is_valid(current_state, new_state):
            raise InvalidStateTransitionError(
                f"Invalid: {current_state} → {new_state}"
            )

        # Update state
        await db.execute("""
            UPDATE core.integrations
            SET status = $1,
                error_message = $2,
                metadata = COALESCE(metadata, '{}'::jsonb) || $3::jsonb,
                updated_at = now()
            WHERE id = $4
        """,
            new_state,
            reason if new_state == IntegrationState.ERROR else None,
            json.dumps(metadata or {}),
            integration_id
        )

        # Log transition
        await db.execute("""
            INSERT INTO ops.events (
                workspace_id,
                actor_type,
                event_type,
                entity_type,
                entity_id,
                payload
            ) VALUES ($1, 'system', $2, 'integration', $3, $4)
        """,
            current['workspace_id'],
            f"integration.state.{new_state}",
            integration_id,
            json.dumps({
                "platform": current['platform'],
                "from_state": current_state,
                "to_state": new_state,
                "reason": reason,
                "metadata": metadata
            })
        )

        # Commit transaction

    # Post-transaction side effects
    await handle_state_transition_side_effects(
        integration_id=integration_id,
        platform=current['platform'],
        from_state=current_state,
        to_state=new_state
    )
```

---

## Monitoring

### Key Metrics

Track these metrics per integration:

```python
# State distribution
SELECT status, COUNT(*) as count
FROM core.integrations
GROUP BY status;

# Average time in each state
SELECT status,
       AVG(EXTRACT(EPOCH FROM (updated_at - connected_at))) as avg_seconds
FROM core.integrations
GROUP BY status;

# Failure rate
SELECT platform,
       COUNT(*) FILTER (WHERE status = 'error') * 100.0 / COUNT(*) as error_rate
FROM core.integrations
GROUP BY platform;

# Recovery time
SELECT platform,
       AVG(recovery_time_seconds) as avg_recovery_time
FROM (
    SELECT
        i.platform,
        EXTRACT(EPOCH FROM (
            e2.created_at - e1.created_at
        )) as recovery_time_seconds
    FROM ops.events e1
    JOIN ops.events e2 ON e1.entity_id = e2.entity_id
    JOIN core.integrations i ON i.id = e1.entity_id::uuid
    WHERE e1.event_type = 'integration.state.error'
      AND e2.event_type IN ('integration.state.active', 'integration.state.connected')
      AND e2.created_at > e1.created_at
) recovery_times
GROUP BY platform;
```

### Alerts

Configure alerts for:

- **High Error Rate:** >10% of integrations in ERROR state
- **Stuck in AUTHORIZING:** Integration in AUTHORIZING for >10 minutes
- **Frequent State Changes:** Integration changing states >10 times/hour
- **Circuit Breakers Open:** >5 integrations with open circuits
- **Token Expiry Spike:** >20% of integrations in EXPIRED state

---

## Conclusion

The Integration State Machine provides a robust framework for managing the complete lifecycle of MCP integrations. By enforcing valid state transitions, logging all changes, and providing clear error recovery paths, we ensure reliable, observable, and maintainable integration behavior across all platforms.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Maintained By:** System Architect
