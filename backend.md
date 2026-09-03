# Event Management System Backend

## 1. Backend Purpose

The backend provides the secure business logic and data services for the Event Management System. It supports two roles:

- **Head User**: Creates and manages owned events.
- **Viewer**: Browses published events and manages personal registrations.

The backend is responsible for authentication, authorization, event lifecycle management, event discovery, registration capacity, validation, and data protection.

## 2. Recommended Backend Architecture

Use a modular monolith with clear internal boundaries:

```text
Client
  |
  v
HTTP API / Controllers
  |
  v
Application Services
  |
  +-- Authentication Module
  +-- User Module
  +-- Event Module
  +-- Discovery Module
  +-- Registration Module
  +-- Notification Adapter
  |
  v
Repositories / Data Access
  |
  +-- Relational Database
  +-- Object Storage
  +-- Email Provider
```

Recommended layers:

- **Routes/controllers**: Parse requests and return HTTP responses.
- **Middleware**: Authentication, authorization, rate limiting, and request correlation.
- **Services**: Coordinate use cases and business rules.
- **Domain models**: Represent users, events, and registrations.
- **Repositories**: Encapsulate database queries.
- **Adapters**: Integrate with image storage and email providers.

Controllers should remain thin. Business decisions such as whether an event can be published or whether a Viewer can register belong in application or domain services.

## 3. Backend Modules

### 3.1 Authentication and User Module

Responsibilities:

- Register users.
- Authenticate credentials.
- Create and destroy sessions.
- Handle password reset requests.
- Return the current user profile.
- Enforce the `HEAD_USER` and `VIEWER` roles.

Security requirements:

- Store only a secure password hash.
- Normalize email addresses before uniqueness checks.
- Use generic sign-in and password-reset responses to avoid account enumeration.
- Expire reset tokens after a short period and invalidate them after use.

### 3.2 Event Module

Responsibilities:

- Create event drafts.
- Update event details.
- Validate event data.
- Publish and unpublish events.
- Cancel events with a reason.
- Delete drafts.
- Verify event ownership.
- Generate management and preview data.

Event statuses:

- `DRAFT`
- `PUBLISHED`
- `UNPUBLISHED`
- `CANCELLED`

Suggested status rules:

```text
DRAFT       -> PUBLISHED, DELETED
PUBLISHED   -> UNPUBLISHED, CANCELLED
UNPUBLISHED -> PUBLISHED, CANCELLED
CANCELLED   -> no further registration or publication
```

A cancelled event should remain stored so its history and cancellation message are not lost.

### 3.3 Discovery Module

Responsibilities:

- List published upcoming events.
- Search event titles and descriptions.
- Filter by date, location, and category when supported.
- Sort by event date or publication date.
- Return public event details.

Public queries must restrict results to events with `PUBLISHED` status. Draft, unpublished, and management-only fields must never be returned by public endpoints.

### 3.4 Registration Module

Responsibilities:

- Create Viewer registrations.
- Prevent duplicate active registrations.
- Check registration windows.
- Enforce event capacity.
- Cancel a Viewer's own registration.
- List registrations for the current Viewer.
- List attendees for the owning Head User.

Registration creation must use a database transaction and row-level locking or an equivalent atomic strategy. A normal read followed by an insert can exceed capacity when concurrent requests arrive.

### 3.5 Notification Adapter

The notification adapter is optional for the MVP. It can support:

- Password reset email.
- Registration confirmation.
- Event cancellation notification.
- Event reminder.

Notification failure should not corrupt the event or registration transaction. Use an asynchronous job or retryable outbox design when notifications become part of the product.

## 4. API Contract

Use JSON request and response bodies with consistent error structures.

### Standard Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid fields.",
    "fields": {
      "title": "Title is required."
    },
    "request_id": "request-id"
  }
}
```

### Authentication Endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `POST` | `/api/auth/signup` | Public | Create an account |
| `POST` | `/api/auth/signin` | Public | Authenticate a user |
| `POST` | `/api/auth/signout` | Authenticated | End the current session |
| `POST` | `/api/auth/password-reset` | Public | Request a password reset |
| `POST` | `/api/auth/password-reset/confirm` | Public | Set a new password |
| `GET` | `/api/me` | Authenticated | Get the current user |
| `PATCH` | `/api/me` | Authenticated | Update profile information |

### Public Event Endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/events` | Public | List published upcoming events |
| `GET` | `/api/events/{eventId}` | Public | Get a published event |

Supported list parameters:

- `search`
- `date_from`
- `date_to`
- `location`
- `category`
- `sort`
- `page`
- `page_size`

### Head User Endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/manage/events` | Head User | List owned events |
| `POST` | `/api/events` | Head User | Create a draft |
| `GET` | `/api/manage/events/{eventId}` | Owner | Get management data |
| `PATCH` | `/api/events/{eventId}` | Owner | Update an event |
| `POST` | `/api/events/{eventId}/publish` | Owner | Publish an event |
| `POST` | `/api/events/{eventId}/unpublish` | Owner | Unpublish an event |
| `POST` | `/api/events/{eventId}/cancel` | Owner | Cancel an event |
| `DELETE` | `/api/events/{eventId}` | Owner | Delete a draft |
| `GET` | `/api/events/{eventId}/attendees` | Owner | List attendees |
| `POST` | `/api/events/{eventId}/cover-image` | Owner | Upload a cover image |

### Viewer Registration Endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `POST` | `/api/events/{eventId}/registrations` | Viewer | Register for an event |
| `GET` | `/api/me/registrations` | Viewer | List personal registrations |
| `DELETE` | `/api/events/{eventId}/registrations/me` | Viewer | Cancel own registration |

## 5. Request Processing

Every protected request should pass through this sequence:

1. Add or propagate a request ID.
2. Apply request size and rate limits.
3. Parse and validate the request body and parameters.
4. Authenticate the user.
5. Check the required role.
6. Check event ownership where applicable.
7. Execute the use case in a service.
8. Commit the database transaction.
9. Return a stable response shape.
10. Record safe operational logs.

Authentication and authorization errors should not reveal whether protected resources exist when that information is sensitive.

## 6. Event Data and Validation

### Event Fields

- `id`: UUID primary key.
- `created_by`: Head User foreign key.
- `title`: Required, bounded string.
- `short_description`: Optional or bounded summary.
- `description`: Required event content.
- `cover_image_url`: Optional object-storage URL.
- `start_time`: UTC timestamp.
- `end_time`: UTC timestamp.
- `timezone`: IANA timezone identifier.
- `venue_name`: Required for physical events.
- `address`: Required for physical events.
- `meeting_url`: Required for online events.
- `organizer_name`: Required.
- `organizer_email`: Valid email address.
- `capacity`: Positive integer.
- `registration_start`: Optional UTC timestamp.
- `registration_end`: Optional UTC timestamp.
- `status`: Controlled status enum.
- `published_at`: Nullable UTC timestamp.
- `cancellation_reason`: Nullable text.
- `created_at` and `updated_at`: UTC timestamps.

### Validation Rules

- End time must be after start time.
- Capacity must be greater than zero.
- Registration end must be after registration start.
- Registration must end no later than the event start.
- The timezone must be a recognized IANA timezone.
- A physical event requires a venue and address.
- An online event requires a valid meeting URL.
- Publishing requires all required fields.
- Cancelled events cannot accept registrations.
- Only drafts may be deleted.

Store timestamps in UTC and use the saved event timezone when formatting values for clients.

## 7. Registration Capacity Algorithm

Registration should use the following transaction:

```text
BEGIN

Lock the event row for update.
Load the event status, registration window, capacity, and current active count.
Reject if the event is not published, is cancelled, or registration is closed.
Reject if the Viewer already has an active registration.
Reject if active registration count is at capacity.
Create the registration.
COMMIT
```

Recommended database protections:

- Unique constraint on `(event_id, viewer_id)` if each Viewer has one registration record per event.
- Registration status such as `ACTIVE` or `CANCELLED`.
- A transaction-safe active registration count.
- `409 Conflict` for full events or duplicate registrations.

## 8. Database Design

### User Table

```text
users
- id UUID PRIMARY KEY
- name VARCHAR NOT NULL
- email VARCHAR NOT NULL UNIQUE
- password_hash VARCHAR NOT NULL
- role VARCHAR NOT NULL
- created_at TIMESTAMP NOT NULL
- updated_at TIMESTAMP NOT NULL
```

### Event Table

```text
events
- id UUID PRIMARY KEY
- created_by UUID NOT NULL REFERENCES users(id)
- title VARCHAR NOT NULL
- short_description VARCHAR
- description TEXT NOT NULL
- cover_image_url VARCHAR
- start_time TIMESTAMP NOT NULL
- end_time TIMESTAMP NOT NULL
- timezone VARCHAR NOT NULL
- venue_name VARCHAR
- address TEXT
- meeting_url VARCHAR
- organizer_name VARCHAR NOT NULL
- organizer_email VARCHAR NOT NULL
- capacity INTEGER NOT NULL
- registration_start TIMESTAMP
- registration_end TIMESTAMP
- status VARCHAR NOT NULL
- published_at TIMESTAMP
- cancellation_reason TEXT
- created_at TIMESTAMP NOT NULL
- updated_at TIMESTAMP NOT NULL
```

### Registration Table

```text
registrations
- id UUID PRIMARY KEY
- event_id UUID NOT NULL REFERENCES events(id)
- viewer_id UUID NOT NULL REFERENCES users(id)
- status VARCHAR NOT NULL
- registered_at TIMESTAMP NOT NULL
- cancelled_at TIMESTAMP
```

Indexes:

- Normalized user email.
- Events by `status` and `start_time`.
- Events by `created_by` and `status`.
- Registrations by `event_id`.
- Registrations by `viewer_id`.
- Unique `(event_id, viewer_id)`.

Use database migrations for every schema change. Do not edit production schemas manually.

## 9. Authorization Rules

- Only authenticated Head Users can create events.
- Only the owning Head User can update, publish, unpublish, cancel, delete, or inspect attendees for an event.
- Only authenticated Viewers can register.
- A Viewer can cancel only their own registration.
- Public endpoints expose only published events.
- A Viewer must never receive private attendee data.
- Role checks and ownership checks must be performed server-side on every request.

Suggested status codes:

- `200 OK`: Successful read or mutation.
- `201 Created`: Resource created.
- `204 No Content`: Successful deletion or cancellation where no body is needed.
- `400 Bad Request`: Malformed request.
- `401 Unauthorized`: Missing or invalid authentication.
- `403 Forbidden`: Authenticated user lacks the required role or ownership.
- `404 Not Found`: Resource does not exist or should not be revealed.
- `409 Conflict`: Capacity, duplicate registration, or state conflict.
- `422 Unprocessable Entity`: Field validation failure.
- `429 Too Many Requests`: Rate limit exceeded.
- `500 Internal Server Error`: Unexpected server failure.

## 10. Security Requirements

- Require HTTPS outside local development.
- Hash passwords with an adaptive password hashing algorithm.
- Use secure, HttpOnly, SameSite cookies for session authentication where possible.
- Add CSRF protection for cookie-authenticated state-changing requests.
- Validate all input on the server.
- Escape or sanitize event content before rendering it in the client.
- Validate image type, size, and content before storage.
- Rate-limit sign-in, password reset, and registration endpoints.
- Keep secrets in environment variables or a secrets manager.
- Do not log passwords, tokens, or unnecessary personal data.
- Configure CORS with an explicit allowed-origin list.
- Use parameterized queries or a trusted ORM to prevent SQL injection.

## 11. File Uploads

Cover images should be uploaded through a controlled backend flow:

1. Authenticate and verify event ownership.
2. Validate content type and maximum size.
3. Scan or inspect the file as required by the deployment environment.
4. Store the file in object storage with a generated name.
5. Save only the resulting safe URL or storage key on the event.
6. Remove replaced files according to a cleanup policy.

Never trust a client-provided filename or content type.

## 12. Error Handling and Logging

Use a central error handler that:

- Converts known domain errors into stable API responses.
- Hides stack traces and internal details in production.
- Includes a request ID in responses and logs.
- Maps validation errors to fields where possible.
- Distinguishes retryable failures from permanent failures.

Log:

- Request ID, route, method, status, and duration.
- Authentication failures without credentials or tokens.
- Event lifecycle changes.
- Registration successes and rejected attempts.
- Database and external-provider failures.

Apply retention and access controls to logs because they may contain operational and personal information.

## 13. Testing Strategy

### Unit Tests

- Password and email validation.
- Role and ownership policies.
- Event field validation.
- Event status transitions.
- Registration eligibility.
- Timezone and registration-window calculations.

### Integration Tests

- Sign-up, sign-in, sign-out, and password reset.
- Event draft creation and editing.
- Publish validation.
- Public visibility filtering.
- Ownership enforcement.
- Registration and cancellation.
- Duplicate registration protection.
- Capacity enforcement.
- Concurrent registration attempts.
- Image upload validation.

### API Contract Tests

Verify endpoint methods, request schemas, response schemas, error codes, pagination, and authorization behavior. Keep the API contract synchronized with the frontend specification.

### End-to-End Tests

- Head User creates and publishes an event.
- Viewer finds and registers for an event.
- Viewer cancels a registration.
- Head User cancels an event.
- Viewer cannot call Head User endpoints.
- A full event rejects additional registrations.

## 14. Performance and Reliability

- Paginate event and attendee lists.
- Add indexes for common discovery and ownership queries.
- Cache public event listings for a short period when traffic requires it.
- Invalidate or bypass cache after publication, unpublishing, editing, or cancellation.
- Use connection pooling for the database.
- Set timeouts for storage and email-provider requests.
- Use retries only for safe or idempotent external operations.
- Add health and readiness endpoints for deployment monitoring.
- Back up the production database and test restoration regularly.

## 15. Configuration

Configuration should be supplied through environment variables or a secrets manager:

```text
APP_ENV
PORT
DATABASE_URL
SESSION_SECRET
FRONTEND_ORIGIN
OBJECT_STORAGE_BUCKET
OBJECT_STORAGE_REGION
EMAIL_PROVIDER_URL
EMAIL_PROVIDER_KEY
LOG_LEVEL
```

Fail startup when required production configuration is missing. Never commit secrets to the repository.

## 16. Suggested Backend Structure

```text
src/
  app/
    server
    routes
    middleware
    errors
  modules/
    auth/
      controller
      service
      repository
      schemas
    users/
    events/
    discovery/
    registrations/
    notifications/
  database/
    migrations
    connection
  infrastructure/
    object-storage
    email
    logging
  shared/
    types
    validation
    pagination
    time
  tests/
    unit
    integration
    e2e
```

## 17. MVP Backend Acceptance Criteria

- Users can register and authenticate securely.
- The backend distinguishes `HEAD_USER` and `VIEWER` roles.
- Only Head Users can create events.
- A new event is saved as a draft.
- Only the owner can manage an event.
- Publishing rejects incomplete or invalid event data.
- Public endpoints return only published events.
- Viewers can register only while registration is open and capacity is available.
- Duplicate and concurrent registrations cannot exceed capacity.
- Viewers can cancel their own registrations.
- Head Users can view attendees for events they own.
- Cancelled events reject new registrations.
- Protected endpoints return appropriate authorization errors.
- Database migrations, automated tests, logging, and production configuration are documented.
