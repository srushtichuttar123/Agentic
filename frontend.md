# Event Management System Frontend

## 1. Frontend Goals

The frontend is a responsive web application for two user types:

- **Viewer**: Discovers published events and manages personal registrations.
- **Head User**: Creates, edits, publishes, cancels, and monitors owned events.

The interface should make event information easy to scan, make event creation clear, and always show the current event status and available actions.

## 2. Frontend Principles

- Use a responsive, mobile-first layout.
- Keep public event discovery simple and fast.
- Show actions only when the current user has permission to use them.
- Validate forms immediately when possible and again on submission.
- Preserve entered form data when an API request fails.
- Provide visible loading, empty, success, error, and unauthorized states.
- Use accessible labels, keyboard navigation, focus states, and sufficient color contrast.
- Display event times using the event's timezone.
- Avoid exposing private attendee or management data in public views.

## 3. Route Map

### Public and Viewer Routes

| Route | Access | Purpose |
|---|---|---|
| `/` | Public | Event discovery page |
| `/events` | Public | Searchable published event list |
| `/events/:eventId` | Public | Event details |
| `/signin` | Public | Sign in |
| `/signup` | Public | Create a Viewer account |
| `/forgot-password` | Public | Request password reset |
| `/profile` | Viewer | View and edit profile |
| `/my-registrations` | Viewer | View and cancel registrations |

### Head User Routes

| Route | Access | Purpose |
|---|---|---|
| `/manage` | Head User | Event management dashboard |
| `/manage/events/new` | Head User | Create an event draft |
| `/manage/events/:eventId/edit` | Head User | Edit an owned event |
| `/manage/events/:eventId/preview` | Head User | Preview an event before publishing |
| `/manage/events/:eventId/attendees` | Head User | View event attendees |

Protected routes must verify the current session and role before rendering the page. The server remains the final authority for authorization.

## 4. Application Shell

### Header

The header should include:

- Application name or logo.
- Link to event discovery.
- Search access on smaller screens.
- Authenticated user menu.
- Head User dashboard link for Head Users.
- Sign in or sign up actions for unauthenticated users.

### Navigation Behavior

- Use a consistent header across public and authenticated pages.
- Use a compact mobile menu on narrow screens.
- Keep the primary action visible on management pages, such as **Create Event**.
- Return focus to the menu trigger after closing the mobile menu.

### Global UI

- Toast or inline notifications for completed actions.
- Global error boundary for unexpected rendering failures.
- Confirmation dialog for destructive actions such as deleting or cancelling.
- Accessible modal behavior with focus trapping and Escape-key support.

## 5. Page Specifications

### 5.1 Event Discovery Page

The discovery page is the default public experience.

Content:

- Page heading.
- Search input.
- Date, location, and category filters.
- Sort control.
- Event result count when available.
- Responsive event grid or list.
- Pagination or load-more control.

Each event result should show:

- Cover image or accessible placeholder.
- Title.
- Short description.
- Date and local time.
- Location.
- Availability status.
- Link to the details page.

States:

- Loading event results.
- No events exist.
- No results match the current filters.
- API request failed.
- More results loading.

### 5.2 Event Details Page

Content:

- Event title and cover image.
- Full description.
- Start and end date/time with timezone.
- Venue, address, or online meeting information.
- Organizer details.
- Registration dates.
- Remaining capacity or Full status.
- Cancellation notice when applicable.
- Registration action for eligible Viewers.

Registration action states:

- `Sign in to register` for unauthenticated users.
- `Register` when registration is open.
- `Registered` when the Viewer has an active registration.
- `Full` when capacity has been reached.
- `Registration closed` outside the registration window.
- `Cancelled` for cancelled events.

Draft and unpublished events must not be available through public event routes.

### 5.3 Head User Dashboard

The dashboard should help a Head User scan and manage owned events.

Content:

- **Create Event** action.
- Event status summary.
- Search and status filter.
- Sort by event date or last updated.
- Event management table on desktop.
- Stacked event rows or cards on mobile.

Each managed event should show:

- Title.
- Event date.
- Status badge.
- Registration count and capacity.
- Last updated time.
- Contextual actions.

Actions by status:

| Status | Available actions |
|---|---|
| Draft | Edit, Preview, Publish, Delete |
| Published | Edit, Preview, Unpublish, Cancel, Attendees |
| Unpublished | Edit, Preview, Publish, Cancel |
| Cancelled | View, Attendees |

### 5.4 Create and Edit Event Form

Organize the form into clear sections:

1. Basic information.
2. Date and time.
3. Location.
4. Organizer details.
5. Registration settings.
6. Cover image.
7. Publishing controls.

Fields:

- Title.
- Short description.
- Full description.
- Cover image.
- Start and end date/time.
- Timezone.
- Venue name.
- Physical address or online meeting link.
- Organizer name and email.
- Capacity.
- Registration start and end dates.

Form behavior:

- Save as Draft should allow incomplete optional content but must validate basic data types.
- Publish should validate every required field.
- Show field-level errors beside the relevant field.
- Keep server validation errors visible after submission.
- Warn before leaving with unsaved changes.
- Disable only the submitted action while a request is in progress.
- Announce success and return to the appropriate event view.

### 5.5 Event Preview Page

The preview should reuse the public event presentation while clearly identifying that it is a preview. It should show:

- The current draft values.
- Missing required fields.
- Current status.
- Edit action.
- Publish action when validation passes.

Preview data must not make an unpublished event publicly discoverable.

### 5.6 Registration and Profile Pages

The registration page or profile section should show:

- Upcoming registrations.
- Past registrations.
- Event title and date.
- Registration status.
- View event action.
- Cancel registration action when allowed.

Cancellation should require confirmation and update the view without a full page reload.

### 5.7 Attendee Page

Only the owning Head User can access an event's attendee page.

Content:

- Event title and status.
- Total registered and capacity.
- Searchable attendee list.
- Viewer name and registration date.
- Registration status.

Do not expose attendee information on public pages.

## 6. Reusable Components

Suggested shared components:

- `AppHeader`
- `UserMenu`
- `ProtectedRoute`
- `RoleGuard`
- `EventCard`
- `EventStatusBadge`
- `AvailabilityBadge`
- `EventFilters`
- `EventList`
- `EventDetails`
- `EventForm`
- `DateTimeFields`
- `LocationFields`
- `RegistrationButton`
- `ConfirmationDialog`
- `EmptyState`
- `LoadingState`
- `ErrorState`
- `Pagination`
- `Toast`

Components should receive data and callbacks through explicit props and should not contain direct authorization decisions that belong to the API.

## 7. Client State and Data Fetching

Separate state into three categories:

### Server State

Data fetched from the API:

- Current user.
- Published event lists.
- Event details.
- Managed events.
- Registrations.
- Attendees.

Use a query and cache strategy that supports loading states, retries, invalidation, and refetching after mutations.

### Form State

Keep event form values, dirty state, field errors, submission state, and upload progress local to the form flow.

### UI State

Keep menus, dialogs, filter panels, toasts, and responsive display state in the UI layer.

After mutations:

- Invalidate the affected event detail query.
- Refresh the relevant dashboard list.
- Refresh registration availability after registration or cancellation.
- Redirect only after the mutation succeeds.

## 8. API Client Contract

Create one frontend API client responsible for:

- Base URL configuration.
- Authentication credentials or token handling.
- JSON serialization and parsing.
- Common error normalization.
- Request cancellation where appropriate.
- Consistent handling of `401`, `403`, `404`, `409`, and validation errors.

Expected frontend behavior:

| Response | UI behavior |
|---|---|
| `401` | Clear session and redirect to sign in when appropriate |
| `403` | Show access denied without exposing protected data |
| `404` | Show not found page |
| `409` | Explain conflict, such as a full event or duplicate registration |
| `422` | Map validation errors to form fields |
| `5xx` | Show retryable server error |

## 9. Event Status Presentation

Use both text and visual styling for status. Color must not be the only indicator.

- Draft: neutral label.
- Published: positive label.
- Unpublished: muted warning label.
- Full: capacity warning label.
- Cancelled: destructive label with cancellation message.
- Registered: confirmation label.

Status labels should remain readable in light and dark display settings if both are supported.

## 10. Accessibility Requirements

- Use semantic landmarks: header, navigation, main, aside, and footer where appropriate.
- Every input must have a visible or programmatically associated label.
- Do not use placeholder text as the only label.
- Maintain a visible keyboard focus indicator.
- Ensure all actions are reachable without a mouse.
- Use `aria-live` for async success and error announcements.
- Provide meaningful alternative text for cover images.
- Mark decorative images as decorative.
- Associate validation messages with their fields.
- Ensure dialogs have accessible names and correct focus management.
- Respect reduced-motion preferences.

## 11. Responsive Layout

### Mobile

- Use a single-column event list.
- Stack form fields when horizontal space is limited.
- Keep registration and primary actions easy to reach.
- Convert dashboard tables into readable stacked rows.
- Make filters collapsible.
- Avoid horizontal scrolling for core workflows.

### Tablet and Desktop

- Use a multi-column event result layout when space allows.
- Use grouped form fields for related date and location inputs.
- Use a dashboard table for comparison and scanning.
- Keep event details readable with a constrained content width.

Use stable image aspect ratios and layout constraints so loading images or changing labels does not shift the page unexpectedly.

## 12. Security Responsibilities in the Frontend

- Treat all client-side role checks as a presentation convenience, not authorization.
- Never put passwords, tokens, or private attendee data in logs.
- Do not store sensitive session data in insecure browser storage when cookie sessions are used.
- Sanitize or safely render event descriptions received from the API.
- Restrict client-side image selection by type and size, while relying on server validation.
- Avoid leaking unpublished event data through browser caches or public URLs.

## 13. Frontend Testing

### Component Tests

- Event status and availability rendering.
- Form field validation and error display.
- Registration button states.
- Protected route behavior.
- Empty, loading, and error states.

### Integration Tests

- Search and filter event discovery.
- Create and save a draft.
- Publish a valid event.
- Reject publishing when required fields are missing.
- Register and cancel a registration.
- Refresh availability after registration.
- Prevent Head User-only controls from appearing for Viewers.

### End-to-End Tests

- Viewer signs up and finds a published event.
- Viewer registers while seats are available.
- Head User creates, previews, and publishes an event.
- Head User edits and cancels an owned event.
- Viewer cannot access management routes.
- Application works at mobile and desktop viewport sizes.

### Accessibility Tests

- Keyboard-only navigation.
- Automated semantic and contrast checks.
- Screen-reader labels for forms and dialogs.
- Focus behavior after route changes and API errors.

## 14. Suggested Frontend Structure

```text
src/
  app/
    routes/
      auth/
      events/
      manage/
      profile/
  components/
    layout/
    feedback/
    forms/
  features/
    auth/
    discovery/
    events/
    registrations/
    management/
  services/
    api-client
    session
  styles/
    tokens
    global
  types/
    auth
    events
    registrations
  utils/
    dates
    errors
```

## 15. MVP Frontend Acceptance Criteria

- A Viewer can browse, search, filter, and open published events.
- An unauthenticated user can see event details and is prompted to sign in before registering.
- A Viewer can register for an available event and see the updated registration state.
- A Viewer can cancel their own registration.
- A Head User can create a draft, edit it, preview it, and publish it.
- A Head User can see owned events and their statuses in a dashboard.
- A Head User can cancel an owned event and provide a cancellation reason.
- Viewers never see Head User management controls or unpublished events.
- Forms provide clear validation, loading, success, and failure feedback.
- Core pages remain usable on mobile, tablet, and desktop screens.
- Core workflows are keyboard accessible.
