````markdown
# 🏥 Bed-Ready Backend Plan (FastAPI)

## 1. System Overview

A dual-interface healthcare system enabling:
- Patients to find and reserve hospital beds in real-time
- Hospitals to manage wards, beds, and incoming reservations

Architecture:
- FastAPI backend (modular services)
- PostgreSQL (preferred) OR MongoDB (adaptable schema)
- Redis (caching + background jobs)
- WebSockets (real-time updates)

---

## 2. Authentication & Users

### Roles
- PATIENT
- HOSPITAL_ADMIN

### User Model
- id (UUID / ObjectId)
- name
- email (unique, indexed)
- password_hash
- role (enum)
- phone (optional)
- created_at

### Auth Flow
1. Signup → hash password (bcrypt)
2. Login → validate credentials → issue tokens
3. Return:
   - access_token (short-lived, e.g., 15 min)
   - refresh_token (long-lived, e.g., 7 days)

### Token Strategy
- JWT (HS256 or RS256)
- Store refresh tokens in DB (blacklist on logout)

### RBAC
- Middleware checks:
  - route access based on role
  - hospital ownership for admin actions

---

## 3. Hospital Profile

### Hospital Model
- id
- hospital_name
- admin_id (FK → User)
- location:
  - lat
  - lng
  - address
- contact_info:
  - phone
  - email
- opening_hours (JSON)
- created_at

### Features
- Create hospital (admin only)
- Update hospital profile
- One admin → one hospital (initially)

---

## 4. Wards & Beds Management

### Ward Model
- id
- hospital_id (FK)
- name (ICU, GENERAL, MATERNITY, ER)
- total_beds
- available_beds (derived or cached)
- created_at

### Bed Model
- id
- ward_id (FK)
- status (AVAILABLE, RESERVED, OCCUPIED)
- reservation_id (nullable)
- created_at

### Core Logic

#### Create Ward
- Input: ward_name, number_of_beds
- Auto-generate N bed records

#### Bed States
- AVAILABLE → free
- RESERVED → held for patient
- OCCUPIED → checked-in

#### Actions
- Reassign bed:
  - change ward_id (only if AVAILABLE)
- Manual toggle:
  - admin can override status
- Delete ward:
  - only if no OCCUPIED beds
  - optionally migrate AVAILABLE beds

---

## 5. Reservation System

### Reservation Model
- id
- user_id (FK)
- hospital_id (FK)
- ward_id (FK)
- bed_id (FK, nullable initially)
- status:
  - PENDING
  - ACCEPTED
  - DECLINED
  - EXPIRED
  - CHECKED_IN
  - CANCELLED
- created_at
- expires_at (created_at + 40 min)

---

### Flow

#### Patient
- Creates reservation (PENDING)

#### Hospital
- Accept:
  - system assigns AVAILABLE bed
  - status → ACCEPTED
  - bed → RESERVED
- Decline:
  - status → DECLINED

---

## 6. Timeout Logic (40-Min Rule)

### Rule
If:
- status = ACCEPTED
- current_time > expires_at
- NOT CHECKED_IN

Then:
- reservation → EXPIRED
- bed → AVAILABLE

### Implementation Options

#### Option A (Recommended)
- Redis + worker (Celery / RQ)
- Queue job at reservation acceptance

#### Option B
- Periodic cron (every 1–5 mins)

---

## 7. Check-In System

### Endpoint
- PATCH /reservations/{id}/checkin

### Logic
- Validate reservation is ACCEPTED
- Update:
  - status → CHECKED_IN
  - bed → OCCUPIED

---

## 8. Search System (Agent-lite)

### Flow
1. User query → LLM parser
2. Convert → structured filters
3. Query DB

### Filters
- ward_type
- availability (available_beds > 0)
- distance (geo query)
- emergency flag

---

### LLM Prompt (Simplified)

```text
Extract:
- ward_type
- emergency
- radius
- availability_required

Return JSON only.
````

---

### Fallback (Non-LLM)

* Keyword matching:

  * "ICU" → ICU
  * "fertility" → MATERNITY
* Default radius: 10km

---

### Geo Query

PostgreSQL:

* PostGIS (ST_DWithin)

MongoDB:

* 2dsphere index

---

## 9. Real-Time Updates

### Events

* bed status change
* reservation accepted/expired

### Implementation

* WebSockets (FastAPI)
* Fallback: polling (every 5–10s)

### Channels

* hospital:{id}
* ward:{id}

---

## 10. Data Models Summary

### Relationships

* User (1) → (1) Hospital
* Hospital (1) → (N) Wards
* Ward (1) → (N) Beds
* Reservation (1) → (1) Bed

---

### Indexing

* User.email (unique)
* Hospital.location (geo index)
* Ward.hospital_id
* Bed.ward_id + status
* Reservation.status + expires_at

---

## 11. API Design (FastAPI)

### Auth

* POST /auth/signup
* POST /auth/login
* POST /auth/refresh

### Hospital

* POST /hospitals
* GET /hospitals/{id}
* PATCH /hospitals/{id}

### Ward

* POST /wards
* GET /wards/{id}
* PATCH /wards/{id}
* DELETE /wards/{id}

### Beds

* PATCH /beds/{id}
* POST /beds/reassign

### Reservations

* POST /reservations
* PATCH /reservations/{id}/accept
* PATCH /reservations/{id}/decline
* PATCH /reservations/{id}/checkin
* PATCH /reservations/{id}/cancel

### Search

* POST /search

---

## 12. System Logic

### Bed Allocation Algorithm

1. Begin transaction
2. Query:

   * SELECT bed WHERE status = AVAILABLE
   * ORDER BY created_at ASC
   * LIMIT 1 FOR UPDATE
3. Assign:

   * bed.status = RESERVED
   * reservation.bed_id = bed.id
4. Commit

---

### Concurrency Handling

* Use DB-level locks:

  * PostgreSQL → SELECT FOR UPDATE
  * MongoDB → atomic updates

---

### Transaction Strategy

* Wrap:

  * reservation accept
  * bed assignment
    in single transaction

---

## 13. Edge Cases

* Double booking:

  * solved via row locking

* Hospital declines after assignment:

  * release bed → AVAILABLE

* User cancels:

  * if RESERVED → release bed

* Ward deletion:

  * block if OCCUPIED beds exist

* System crash during reservation:

  * recovery job scans inconsistent states

---

## 14. Scalability Notes

### Horizontal Scaling

* Stateless FastAPI instances
* Load balancer

### Redis

* caching search results
* background jobs
* pub/sub for real-time

### Read vs Write

* Read replicas (Postgres)
* Cache frequent queries

---

## 15. Optional Nice-to-Haves

* Hospital ratings & reviews
* Verified hospital badge
* Admin analytics dashboard:

  * occupancy rate
  * avg response time
* Audit logs (critical for healthcare)

---

## 16. Suggested Folder Structure

```
app/
  api/
  models/
  schemas/
  services/
  core/
  workers/
  db/
```

---

## 17. Key Design Principles

* Strong consistency for bed allocation
* Event-driven updates
* Minimal coupling between modules
* Clear state transitions

---

```
```
