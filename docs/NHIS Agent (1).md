**NHIS Patient Rights & Entitlement Agent**

Product & System Design Brief

*For Frontend & Backend Engineers*

Ashesi University  |  ICS NLP Group Project  |  2025

**1\. Project Overview**

This document describes the web application design for the NHIS Patient Rights and Entitlement Agent — a conversational AI system that helps Ghanaian NHIS subscribers understand their rights, check coverage entitlements, locate accredited facilities, and navigate disputes when facilities wrongly charge or turn them away.

 

| *Core value: The average NHIS subscriber has little idea what they are actually entitled to. This platform closes that information gap through a simple, conversational interface grounded in official NHIS policy.* |
| :---- |

 

**Target Users**

• Ghanaian citizens enrolled in NHIS seeking coverage guidance

• Patients who have been charged unexpectedly or turned away from facilities

• Caregivers managing a family member's healthcare navigation

 

**2\. Application Structure & Pages**

The application has 8 distinct pages/screens. These are described below with their purpose, key content, and design notes.

 

**2.1  Landing Page  (Public)**

• Hero section with a clear one-line value proposition: "Know your NHIS rights. Ask anything."

• Brief explainer of what the agent can help with — 3 to 4 illustrated use cases (e.g. checking drug coverage, finding accredited facilities)

• Call to action: Sign Up and Get Started / Log In

• Trust signals: NHIS branding acknowledgement, data privacy statement

• Link to the Resource Centre for users who want to browse without signing up

 

**2.2  Sign Up & Login  (Auth Pages)**

**Sign Up — Fields to collect:**

• Full name

• Email address (for account and notifications)

• Phone number (optional — for SMS renewal reminders)

• Region of residence (used to bias facility search results)

• NHIS membership number (used to estimate renewal window and personalise guidance)

• NHIS membership type: Standard / Informal / SSNIT / Indigent

• Password

 

| *Note to backend: NHIS number is stored locally and used only for renewal tracking and personalisation. We are not integrating with NHIS backend systems — the renewal estimate is calculated from the standard 12-month renewal cycle.* |
| :---- |

 

**Login:**

• Email \+ password

• Forgot password flow via email

 

**2.3  Dashboard / Home  (Post-Login Landing)**

This is the first screen a user sees after logging in. It should feel like a personal health information hub, not a generic homepage.

 

**Key components:**

• **Top of page:** Membership Status Card

    Shows: NHIS number (masked), membership type, estimated expiry date, renewal status badge (Active / Expiring Soon / Expired), and a one-click Renew button that links to NHIS renewal guidance.

 

• **Below status card:** Quick Actions Row

    Shortcut buttons: Ask the Agent, Find a Facility, Check Drug Coverage, My Rights.

 

• **Middle section:** Recent Conversations

    Last 3 agent conversations with timestamps, each clickable to reopen.

 

• **Bottom:** Health Updates Strip

    Latest 3 updates from Ghana Health Service or NHIS — title and date only, with a See All link to the full Health Updates page.

 

**2.4  Agent Chat Page  (Core Feature)**

This is the most important page in the application. Design should prioritise clarity and trust.

 

**Layout:**

• Left sidebar: conversation history list (collapsible on mobile)

• Main panel: active conversation thread

• Input bar at bottom: text input \+ send button \+ optional voice input icon

 

**Conversation thread features:**

• User messages right-aligned, agent messages left-aligned

• Agent responses include a source tag below each message: e.g. 'Source: NHIS Benefit Package 2023, Section 4' — this is critical for building user trust and is a core research feature

• Suggested follow-up questions rendered as tappable chips below each agent response (e.g. 'How do I appeal this?' / 'Which facilities near me cover this?')

• If the agent cannot find an answer in its knowledge base, it displays a clear fallback: 'I could not find this in the NHIS guidelines. Please contact NHIS directly on 0800-900-9900'

 

**Supported query types the agent handles:**

• Coverage queries: 'Is caesarean section covered under NHIS?'

• Drug entitlement: 'Should I pay for amoxicillin at an NHIS facility?'

• Facility accreditation: 'Is Korle Bu Teaching Hospital NHIS-accredited?'

• Membership and renewal: 'My card expired — what do I do?'

• Rights disputes: 'They turned me away — is that allowed?'

 

| *Design note: The source attribution below each agent message is not optional — it is a core research feature that differentiates this system from generic chatbots and helps users verify responses independently.* |
| :---- |

 

**2.5  Facility Finder Page**

A dedicated page for locating nearby NHIS-accredited healthcare facilities — separate from the chat interface for discoverability.

 

• Search bar: search by facility name, town, or region

• Filter options: facility type (hospital / clinic / pharmacy / diagnostic centre), region

• Results list with facility name, type, region, and accreditation status badge

• Map view toggle: pins showing facility locations (integrate Google Maps or OpenStreetMap)

• Clicking a facility shows a detail panel: address, services covered, contact number

 

| *Backend note: The facility data comes from the NHIS accredited facilities list, stored as a structured database table — not the vector store. Queries here are exact/fuzzy text matches, not semantic search.* |
| :---- |

 

**2.6  Resource Centre  (Blog \+ FAQ)**

A unified content hub replacing separate blog and FAQ pages. Organised by category so users can browse or search.

 

**Categories:**

• Understanding Your NHIS Card — membership types, what the card covers, how to use it

• Your Rights as a Patient — what facilities can and cannot do, how to dispute

• Covered Services — summaries of what NHIS covers by condition type

• Medicines Guide — how to know if a drug is on the NHIS formulary

• Enrollment & Renewal — step-by-step guides

• FAQs — top 20 frequently asked questions, each with a short answer and a 'Ask the Agent for more' button

 

Each article has: title, category tag, read time estimate, and a share button. Articles are written by the project team and grounded in official NHIS documentation.

 

**2.7  Health Updates Page  (News Feed)**

Curated updates relevant to NHIS subscribers — not raw news, but filtered and summarised for relevance.

 

**Content sources:**

• Ghana Health Service official announcements

• NHIS official communications (new covered drugs, policy changes, accreditation updates)

• National health alerts (disease outbreaks, vaccination drives)

 

**Display format:**

• Card layout: headline, source, date, 2-line summary, Read More link

• Filter by category: Policy Updates / Drug Formulary / Disease Alerts / General Health

 

| *Backend note: In the first version, this content can be manually curated and stored in a simple CMS table. Automated scraping of GHS/NHIS websites can be added in a later iteration.* |
| :---- |

 

**2.8  Profile & Settings Page**

• Edit personal details: name, phone, region

• NHIS membership info: view/update NHIS number and membership type

• Notification preferences: email or SMS renewal reminders (toggle on/off, set how many days before expiry)

• Conversation history: view and delete past agent conversations

• Account: change password, delete account

 

**3\. Key User Flows**

 

**Flow 1 — New User Onboarding**

Landing Page  →  Sign Up (enter details incl. NHIS number)  →  Dashboard (see membership status populated)  →  First agent conversation prompted by a suggested starter question

 

**Flow 2 — Coverage Question**

Dashboard  →  Tap 'Ask the Agent'  →  Type query  →  Agent retrieves relevant NHIS policy, responds with source attribution  →  User taps suggested follow-up  →  Agent responds  →  User satisfied or directed to escalate to NHIS

 

**Flow 3 — Drug Entitlement Check**

Chat page  →  'I was charged GHS 30 for paracetamol at an NHIS clinic, should I pay this?'  →  Agent queries medicines tool  →  Returns coverage status  →  If covered, agent explains patient's right to dispute and provides exact steps

 

**Flow 4 — Renewal Reminder**

User receives email/SMS 30 days before estimated expiry  →  Clicks link  →  Lands on Dashboard with renewal banner highlighted  →  Taps 'Renew' — links to NHIS renewal guidance in Resource Centre

 

**4\. System Architecture Overview**

 

| *This section gives backend engineers a high-level view of how the agent works behind the interface. A more detailed technical spec will follow separately.* |
| :---- |

 

**4.1  Core Components**

 

| Component | Purpose | Technology (suggested) |
| :---- | :---- | :---- |
| Web Frontend | User interface — all pages described above | React \+ Tailwind CSS |
| Backend API | Request routing, auth, session management | FastAPI (Python) |
| Agent Layer | Reasoning over user queries using ReAct framework | LangChain / custom prompt orchestration |
| Vector Store | Semantic search over NHIS narrative policy documents | ChromaDB or FAISS |
| Structured DB | Accredited facilities list, medicines formulary, user accounts | PostgreSQL |
| LLM | Core language model powering agent responses | GPT-4o or Claude via API |
| Auth | User authentication and session management | JWT-based auth |
| Notification Service | Email/SMS renewal reminders | SendGrid / Twilio |

 

**4.2  Agent Tools**

The agent has three tools it can call depending on the user's query:

 

| Tool | What it searches | Search method |
| :---- | :---- | :---- |
| Policy Retriever | NHIS benefit package, membership guidelines, rights documents | Semantic search — Vector Store |
| Medicines Checker | NHIS Essential Medicines List (drug formulary) | Exact/fuzzy lookup — Structured DB |
| Facility Checker | NHIS accredited facilities by name and region | Exact/fuzzy lookup — Structured DB |

 

The agent decides which tool(s) to call based on the user's query. It reasons step by step (ReAct pattern) before generating a response. Responses are grounded only in retrieved context — the agent does not answer from general knowledge to prevent hallucination.

 

**4.3  Data Sources**

• NHIS Benefit Package Document — public PDF from nhis.gov.gh

• NHIS Essential Medicines List — public document from nhis.gov.gh

• NHIS Accredited Facilities List — public directory from nhis.gov.gh

• NHIS Membership & Renewal Guidelines — public documentation

• Ghana Health Service health alerts — nhis.gov.gh / ghanahealthservice.org

 

| *All data sources are publicly available. No integration with NHIS internal systems is required. The knowledge base is constructed by downloading, cleaning, and indexing these documents.* |
| :---- |

 

**4.4  What the Agent Will and Will Not Do**

 

| Will Do | Will NOT Do |
| :---- | :---- |
| Answer coverage and entitlement questions | Access or verify live NHIS membership databases |
| Explain NHIS policy in plain language | Submit claims or appeals on behalf of users |
| Identify if a drug is on the NHIS formulary | Guarantee accuracy of renewal dates (estimated only) |
| List accredited facilities by region | Provide medical diagnosis or clinical advice |
| Explain user rights in a dispute | Contact facilities or insurers directly |
| Acknowledge when it does not know something | Answer questions outside NHIS scope |

 

**5\. UI/UX Design Notes**

 

• Mobile-first design — majority of Ghanaian users will access on mobile

• Keep colour palette clean and trustworthy — suggest white, deep blue, green accents (aligned with healthcare context)

• All key actions must be reachable within 2 taps from the dashboard

• Source attribution in the chat is non-negotiable — display it visually distinct but not intrusive (small tag below each agent bubble)

• Offline awareness — show a clear banner if connectivity is lost rather than silent failure

• Language: English only for v1. Twi/French localisation noted as future work

• Accessibility: sufficient contrast ratios, readable font sizes minimum 16px on mobile

 

**6\. Out of Scope for Version 1**

• Live integration with NHIS membership database

• Claim submission or appeals submission

• Automated news scraping (manual curation for v1)

• Twi or other local language support

• Mobile native app (web app only for v1)

 

*NHIS Agent Project — Ashesi University NLP Group  |  Document version 1.0  |  2025*  
