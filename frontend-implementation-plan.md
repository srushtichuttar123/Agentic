# Frontend Implementation Plan

## 1. Source of Truth

`idea.md` is the product source of truth. It defines the required users, permissions, workflows, data, and MVP behavior.

Use the supporting documents as implementation guidance:

- `frontend.md`: Routes, screens, components, UI states, accessibility, and responsive behavior.
- `backend.md`: REST endpoints, authorization, response codes, validation, and backend data contracts.
- `database.md`: Entity fields, statuses, capacity rules, and date/time behavior.

When documents conflict, preserve the user-facing behavior in `idea.md` and update the supporting documentation before implementation.

## 2. Frontend MVP Outcome

The completed MVP frontend must allow:

- A Viewer to sign up, sign in, discover published upcoming events, search, filter, view details, register, and cancel a registration.
- A Head User to sign in, create a draft event, edit it, preview it, publish it, unpublish it, cancel it, delete drafts, and view attendees for owned events.
- Both roles to receive clear loading, empty, validation, error, success, and unauthorized states.
- All core workflows to work on mobile, tablet, and desktop layouts.
- Frontend calls to match the backend API contract and never replace server-side authorization.

## 3. Implementation Phases

### Phase 0: Contract and Project Setup

**Tasks**

- Choose the frontend framework and package manager.
- Create the frontend application structure described in `frontend.md`.
- Configure environment-based API URL settings.
- Add TypeScript types or equivalent schemas for User, Event, Registration, and API errors.
- Define route constants and role constants.
- Create a single API client for all backend requests.
- Add a consistent error-normalization function for `401`, `403`, `404`, `409`, `422`, and `5xx` responses.
- Configure formatting, linting, and test commands.

**Exit criteria**

- The application starts locally.
- A health-check request can reach the backend.
- API responses and errors are represented by typed client models.
- No feature makes direct ad hoc HTTP calls outside the API client.

### Phase 1: Application Shell and Design Foundation

**Tasks**

- Build the shared application header and navigation.
- Add public navigation to event discovery.
- Add authenticated user menu and sign-out action.
- Show the Head User dashboard link only for Head Users.
- Implement mobile navigation with correct focus return behavior.
- Define design tokens for typography, colors, spacing, borders, focus states, and status colors.
- Add shared Loading, Empty, Error, Toast, and Confirmation Dialog components.
- Add a global error boundary.

**Exit criteria**

- The shell renders at mobile and desktop widths.
- Keyboard focus is visible and predictable.
- Async notifications are announced accessibly.
- Destructive actions use confirmation.

### Phase 2: Authentication and Session Handling

**Tasks**

- Build sign-up form.
- Build sign-in form.
- Build sign-out flow.
- Build password-reset request screen when the backend endpoint is available.
- Fetch and cache the current user from `/api/me`.
- Persist only the session mechanism supported by the backend.
- Implement session expiration handling and redirect to `/signin` after `401` responses.
- Add protected-route and role-guard behavior.
- Preserve intended destination when redirecting an unauthenticated user to sign in.

**Exit criteria**

- A Viewer can create an account and sign in.
- A Head User can sign in.
- Invalid credentials and validation errors are displayed clearly.
- Signed-out users cannot access protected routes.
- Viewers cannot access Head User routes.
- The UI never treats client-side role checks as authorization.

### Phase 3: Viewer Event Discovery

**Tasks**

- Build the `/` and `/events` discovery screens.
- Connect event listing to `GET /api/events`.
- Add search input with deliberate request behavior, such as submit or debouncing.
- Add date, location, and category filters when supported by the backend.
- Add sorting and pagination controls based on the API response contract.
- Build reusable EventCard and EventList components.
- Display title, summary, cover image, date, timezone, location, and availability.
- Add loading, empty, no-results, retry, and server-error states.
- Keep filters represented in URL query parameters so results can be shared and revisited.

**Exit criteria**

- Only published upcoming events are displayed.
- Search and supported filters produce correct API requests.
- Refreshing or sharing a filtered URL preserves the view.
- Event cards are usable by keyboard and screen readers.
- Layout remains usable without horizontal scrolling on mobile.

### Phase 4: Event Details and Viewer Registration

**Tasks**

- Build `/events/:eventId` using `GET /api/events/{eventId}`.
- Display event content, local timezone, location, organizer, capacity, and notices.
- Implement registration button states: sign in, register, registered, full, closed, and cancelled.
- Connect registration to `POST /api/events/{eventId}/registrations`.
- Connect cancellation to `DELETE /api/events/{eventId}/registrations/me`.
- Handle `409` conflicts for full events and duplicate registrations.
- Refresh event availability and personal registration data after mutations.
- Add confirmation before cancellation.

**Exit criteria**

- A Viewer can register for an available event.
- The interface reflects the updated registration state without stale data.
- A full, closed, or cancelled event cannot be registered for.
- An unauthenticated user is sent to sign in before registration.
- The Viewer can cancel only their own registration through the supported flow.

### Phase 5: Viewer Profile and Registrations

**Tasks**

- Build `/profile`.
- Build `/my-registrations` using `GET /api/me/registrations`.
- Separate upcoming and past registrations.
- Show registration status and event details.
- Add view-event and cancel-registration actions.
- Add empty and unavailable states.
- Add profile editing after the backend profile endpoint is available.

**Exit criteria**

- A Viewer can see their registrations.
- Cancellation updates the list and event availability.
- Another Viewer's registrations cannot be requested or displayed.

### Phase 6: Head User Dashboard

**Tasks**

- Build `/manage` using `GET /api/manage/events`.
- Add status summary for Draft, Published, Unpublished, and Cancelled events.
- Add search, status filtering, sorting, and pagination as supported.
- Build responsive management table and mobile stacked rows.
- Add status badges with text plus visual treatment.
- Add contextual actions based on event status.
- Add ownership-safe navigation to edit, preview, and attendee pages.

**Exit criteria**

- A Head User sees only owned events.
- Each event displays status, date, capacity, registration count, and last update.
- Invalid actions are not offered for the current status.
- The dashboard remains scannable on mobile.

### Phase 7: Event Creation, Editing, Preview, and Lifecycle

**Tasks**

- Build `/manage/events/new`.
- Build `/manage/events/:eventId/edit`.
- Implement grouped event form sections:
  - Basic information.
  - Date and time.
  - Location.
  - Organizer details.
  - Registration settings.
  - Cover image.
- Save drafts through `POST /api/events`.
- Update events through `PATCH /api/events/{eventId}`.
- Build `/manage/events/:eventId/preview`.
- Publish through `POST /api/events/{eventId}/publish`.
- Unpublish through `POST /api/events/{eventId}/unpublish`.
- Cancel through `POST /api/events/{eventId}/cancel` with a required reason.
- Delete drafts through `DELETE /api/events/{eventId}`.
- Warn about unsaved changes.
- Preserve form values after network or validation errors.

**Exit criteria**

- A new event starts as a Draft.
- Draft saving does not expose the event publicly.
- Publishing blocks incomplete or invalid data.
- Published, Unpublished, and Cancelled states are reflected immediately.
- Only the owning Head User can perform management actions.
- Cancel requires a reason and prevents future registration.
- Only Draft events can be deleted.

### Phase 8: Attendee Management

**Tasks**

- Build `/manage/events/:eventId/attendees`.
- Connect to `GET /api/events/{eventId}/attendees`.
- Display attendee name, email, registration date, and status.
- Display active count against capacity.
- Add attendee search or pagination when supported.
- Handle forbidden and not-found responses without exposing private data.

**Exit criteria**

- Only the owning Head User can access attendees.
- Public event pages never contain private attendee details.
- Attendee lists remain usable on mobile.

### Phase 9: Accessibility, Responsive Quality, and Hardening

**Tasks**

- Test all routes with keyboard-only navigation.
- Verify labels, descriptions, validation associations, dialog names, and live announcements.
- Check color contrast and ensure status is not communicated by color alone.
- Test mobile, tablet, and desktop viewport sizes.
- Respect reduced-motion preferences.
- Add retry behavior for transient API failures.
- Add optimistic updates only where rollback behavior is defined.
- Review browser caching for unpublished data and private attendee data.

**Exit criteria**

- Core workflows pass accessibility checks.
- No text, buttons, forms, or tables overflow at supported widths.
- Loading and error states do not cause confusing layout shifts.
- Unauthorized and forbidden states are clear and non-leaky.

## 4. Frontend API Integration Matrix

| Frontend feature | API call | Access | Expected result |
|---|---|---|---|
| Sign up | `POST /api/auth/signup` | Public | Account created |
| Sign in | `POST /api/auth/signin` | Public | Session/token returned |
| Sign out | `POST /api/auth/signout` | Authenticated | Session invalidated |
| Current user | `GET /api/me` | Authenticated | User and role returned |
| Event discovery | `GET /api/events` | Public | Published upcoming events |
| Event details | `GET /api/events/{eventId}` | Public | Public event data |
| Viewer registration | `POST /api/events/{eventId}/registrations` | Viewer | Active registration created |
| Viewer cancellation | `DELETE /api/events/{eventId}/registrations/me` | Viewer | Registration cancelled |
| Viewer registrations | `GET /api/me/registrations` | Viewer | Own registrations returned |
| Managed events | `GET /api/manage/events` | Head User | Owned events returned |
| Create draft | `POST /api/events` | Head User | Draft created |
| Update event | `PATCH /api/events/{eventId}` | Owner | Event updated |
| Publish | `POST /api/events/{eventId}/publish` | Owner | Event published |
| Unpublish | `POST /api/events/{eventId}/unpublish` | Owner | Event unpublished |
| Cancel | `POST /api/events/{eventId}/cancel` | Owner | Event cancelled |
| Delete draft | `DELETE /api/events/{eventId}` | Owner | Draft deleted |
| Attendees | `GET /api/events/{eventId}/attendees` | Owner | Private attendee list returned |

## 5. Backend Contract Gaps to Resolve First

The current backend MVP has been verified for the core event and registration workflows. Before implementing dependent frontend screens, complete or explicitly defer these documented calls:

- Password-reset request and confirmation.
- Profile update through `PATCH /api/me`.
- Cover-image upload.
- Category filtering.
- Date and location filtering.
- Pagination metadata and controls.

For every deferred call, the frontend should show a deliberate unavailable state or hide the feature from the MVP. Do not build a UI that silently calls an endpoint that does not exist.

## 6. Testing Plan

### Unit Tests

- API client URL, method, headers, and body construction.
- API error normalization.
- Date and timezone formatting.
- Event status action availability.
- Registration button state calculation.
- Form validation.
- Role and route-guard decisions.

### Component Tests

- EventCard and EventDetails rendering.
- Event filters and query synchronization.
- EventForm field errors and dirty state.
- Status and availability badges.
- Registration and cancellation states.
- Dialog focus behavior.
- Loading, empty, and error states.

### Integration Tests

- Sign in and current-user loading.
- Viewer event discovery and search.
- Viewer registration and cancellation.
- Head User draft creation and publishing.
- Event update and lifecycle actions.
- Ownership and role error handling.
- Attendee list access.

### End-to-End Tests

1. Viewer signs up and signs in.
2. Viewer searches for a published event.
3. Viewer opens event details and registers.
4. Viewer sees the registration in their profile.
5. Viewer cancels the registration.
6. Head User signs in and creates a draft.
7. Head User previews and publishes the event.
8. Viewer discovers the newly published event.
9. Head User unpublishes or cancels the event.
10. Viewer can no longer register for the unavailable event.
11. A Viewer cannot access Head User routes.
12. A Head User cannot manage another Head User's event.

### Accessibility and Responsive Tests

- Keyboard-only walkthrough of every MVP workflow.
- Automated accessibility scan for each primary route.
- Mobile, tablet, and desktop screenshots.
- Reduced-motion behavior.
- Long titles, long descriptions, validation errors, and empty states.

## 7. Delivery Checklist

- [ ] Frontend project starts locally.
- [ ] API base URL is configurable.
- [ ] API client is the only HTTP integration point.
- [ ] Authentication and role guards work.
- [ ] Viewer discovery and event details work.
- [ ] Viewer registration and cancellation work.
- [ ] Head User dashboard works.
- [ ] Event draft, edit, preview, publish, unpublish, cancel, and delete flows work.
- [ ] Attendee list works for owners only.
- [ ] Loading, empty, error, unauthorized, and conflict states are implemented.
- [ ] Forms preserve data and show field-level errors.
- [ ] Accessibility checks pass.
- [ ] Responsive checks pass.
- [ ] Integration and end-to-end tests pass.
- [ ] Backend contract gaps are either implemented or explicitly deferred.

## 8. Definition of Done

The frontend is ready for MVP handoff when every `idea.md` core workflow is executable through the UI, each protected action is backed by the corresponding verified API call, published-event visibility matches the backend, registration capacity and conflict states are handled correctly, and the application passes the frontend, accessibility, responsive, and end-to-end checks above.
