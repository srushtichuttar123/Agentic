# Event Management System

## 1. Product Overview

The Event Management System is a web application for creating, organizing, and viewing events. It supports two user roles:

1. **Head User** - Creates and manages events.
2. **Viewer** - Browses published events and views their details.

The system should provide a simple, reliable way for event organizers to share accurate event information with attendees.

## 2. Goals

- Allow Head Users to create and manage events.
- Allow Viewers to find and view published events.
- Keep event information organized and easy to update.
- Protect event management actions from unauthorized users.
- Provide a responsive experience on desktop and mobile devices.

## 3. User Roles and Permissions

### Head User

A Head User can:

- Create an event.
- Edit event details.
- Publish or unpublish an event.
- Cancel or delete an event.
- View a list of events they manage.
- Search and filter their events.
- See the event status: Draft, Published, Unpublished, or Cancelled.
- Manage basic attendee information when attendee registration is enabled.

### Viewer

A Viewer can:

- Create an account or sign in.
- Browse published events.
- Search and filter events.
- Open an event details page.
- View the event title, description, date, time, location, organizer, and available capacity.
- Register for an event when registration is enabled.
- View or cancel their own registration.

A Viewer cannot create, edit, publish, or delete events.

## 4. Core Features

### Authentication and Accounts

- Sign up and sign in.
- Sign out securely.
- Password reset.
- Role-based access control.
- A user profile containing name and contact information.

### Event Creation

A Head User must be able to create an event with the following information:

- Event title.
- Short description.
- Full description.
- Cover image, if available.
- Start date and time.
- End date and time.
- Venue name.
- Full address or online meeting link.
- Organizer name and contact details.
- Maximum attendee capacity.
- Registration start and end dates.
- Event visibility.
- Event status.

New events should start as **Drafts**. A Head User must explicitly publish an event before Viewers can see it.

### Event Management

- Edit a draft or published event.
- Save changes without publishing them.
- Publish an event.
- Unpublish an event temporarily.
- Cancel an event with a cancellation message.
- Delete a draft event.
- Prevent publishing when required fields are missing.

### Event Discovery

Viewers should have access to:

- A list of published upcoming events.
- Search by event title or keyword.
- Filters for date, location, and category.
- Sorting by date or newest publication.
- A clear empty state when no events match the search.

### Event Details

Each published event page should show:

- Title and cover image.
- Description.
- Date and time with timezone.
- Location or online meeting link.
- Organizer information.
- Remaining capacity.
- Registration status.
- Cancellation or update notices.

### Registration

When registration is enabled:

- Viewers can register while seats are available.
- The system must prevent registrations beyond the capacity limit.
- A Viewer can see their registration status.
- A Viewer can cancel their registration before the event.
- The Head User can view registered attendees.
- The system can mark an event as Full when capacity is reached.

## 5. Main Workflows

### Head User Creates an Event

1. The Head User signs in.
2. The Head User selects **Create Event**.
3. The Head User enters the required event information.
4. The system validates the information.
5. The event is saved as a Draft.
6. The Head User previews the event.
7. The Head User publishes the event.
8. The event becomes visible to Viewers.

### Viewer Finds an Event

1. The Viewer opens the event listing.
2. The Viewer searches or applies filters.
3. The Viewer selects an event.
4. The system displays the event details.
5. The Viewer registers if registration is available.

### Head User Cancels an Event

1. The Head User opens a managed event.
2. The Head User selects **Cancel Event**.
3. The Head User enters a cancellation reason.
4. The system changes the status to Cancelled.
5. Viewers see the cancellation notice and cannot register.

## 6. Suggested Pages

- Landing or event discovery page.
- Sign in page.
- Sign up page.
- Viewer event listing page.
- Event details page.
- Viewer profile and registrations page.
- Head User dashboard.
- Create event page.
- Edit event page.
- Event preview page.
- Attendee list page.

## 7. Basic Data Model

### User

- `id`
- `name`
- `email`
- `password_hash`
- `role`
- `created_at`
- `updated_at`

### Event

- `id`
- `created_by`
- `title`
- `short_description`
- `description`
- `cover_image_url`
- `start_time`
- `end_time`
- `timezone`
- `venue_name`
- `address`
- `meeting_url`
- `organizer_name`
- `organizer_email`
- `capacity`
- `registration_start`
- `registration_end`
- `status`
- `created_at`
- `updated_at`

### Registration

- `id`
- `event_id`
- `viewer_id`
- `status`
- `registered_at`
- `cancelled_at`

## 8. Functional Requirements

- The system must distinguish between Head Users and Viewers.
- Only Head Users can create events.
- Only the Head User who owns an event can edit, publish, cancel, or delete it.
- Required fields must be validated before an event can be published.
- Only published events appear in the Viewer event listing.
- Event times must display consistently with the event timezone.
- The system must prevent duplicate registrations for the same Viewer and event.
- The system must enforce the event capacity.
- Cancelled events must remain identifiable and must not accept registrations.
- Unauthorized users must receive an appropriate access-denied response.

## 9. Non-Functional Requirements

- Responsive on common desktop, tablet, and mobile screen sizes.
- Secure password storage and authenticated API requests.
- Server-side authorization checks for every protected action.
- Clear validation and error messages.
- Accessible forms, labels, keyboard navigation, and sufficient color contrast.
- Reliable date and timezone handling.
- Regular database backups in production.
- The application should load common pages quickly under normal usage.

## 10. MVP Scope

The first version should include:

- Authentication.
- The two user roles.
- Head User dashboard.
- Event creation and editing.
- Draft and Published statuses.
- Event discovery and event details pages.
- Viewer registration and cancellation.
- Capacity validation.
- Basic responsive design.

## 11. Future Enhancements

- Multiple Head Users and organization accounts.
- Event categories and tags.
- Email confirmations and reminders.
- Calendar export.
- QR-code check-in.
- Payments and ticket types.
- Recurring events.
- Analytics dashboard.
- Comments, ratings, and event feedback.
- Social sharing.

## 12. MVP Acceptance Criteria

- A Head User can sign in, create a valid event, save it as a Draft, and publish it.
- A published event is visible to Viewers and has a working details page.
- A Viewer can register for an available event.
- A Viewer cannot register after capacity is reached or after registration closes.
- A Viewer cannot access Head User event-management actions.
- A Head User can edit or cancel an event they own.
- A cancelled or unpublished event is not shown as an available public event.
- The system validates required fields and displays useful errors.
- The main workflows work on both desktop and mobile layouts.
