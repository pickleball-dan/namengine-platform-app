# NamEngine Provisional Patent — USPTO Filing Guide
**Prepared:** 2026-09-08

A provisional patent application (PPA) establishes your **priority date** — the date the USPTO considers your invention "filed." You then have **12 months** to file a full non-provisional application claiming that priority date. The PPA itself is never examined and never becomes a patent on its own; it buys you time and the "patent pending" designation.

---

## Before You File — What You Need

### 1. Create a USPTO Account
- Go to **https://my.uspto.gov**
- Click "Create an account"
- You'll need a valid email address
- This account is used for all future patent filings, so keep the credentials safe

### 2. Determine Your Entity Status (affects the fee)

| Status | Who qualifies | Filing fee |
|---|---|---|
| **Micro Entity** | Individual inventor, income under ~$239K/yr, fewer than 5 prior patent filings | **~$160** |
| **Small Entity** | Individual, small business (<500 employees), nonprofit | **~$320** |
| **Large Entity** | Corporation/entity that doesn't qualify above | **~$1,760** |

As a solo founder, you almost certainly qualify for **Micro Entity** status. This is the cheapest path.

### 3. Prepare Your Documents

You need two files:
- **The specification** — this is `namengine-provisional-patent.md` converted to PDF (instructions below)
- **Application Data Sheet (ADS)** — a standard USPTO form; Patent Center generates one for you during filing

You do **not** need:
- Formal patent claims (though we've included indicative claims)
- Formal drawings (though you can include screenshots/diagrams)
- An oath or declaration

---

## Step-by-Step Filing in USPTO Patent Center

### Step 1 — Convert the Specification to PDF

Open `namengine-provisional-patent.md` and export/convert it to PDF. Options:
- **VS Code**: install "Markdown PDF" extension → right-click → "Export (pdf)"
- **Word/Google Docs**: paste the content → File → Save as PDF
- **Browser**: open the .md file in a Markdown viewer (e.g., Markdown Preview in VS Code), print to PDF
- The PDF should be clean, readable, 12pt font, with the title clearly at the top

### Step 2 — Go to Patent Center

Navigate to: **https://patentcenter.uspto.gov**

Log in with your USPTO account (created in Before You File, Step 1).

### Step 3 — Start a New Application

1. Click **"File"** in the top navigation
2. Select **"Provisional Application"**
3. Click **"Start New Application"**

### Step 4 — Enter Application Details

You'll be prompted for basic information:

| Field | What to enter |
|---|---|
| **Application type** | Provisional |
| **Title of invention** | System and Method for Personalized Name Generation Using Structured Preference Elicitation, Canonical Intent Mapping, Reaction-Driven Refinement, and Multi-Provider Quality Routing |
| **Inventor name** | Your legal name |
| **Inventor address** | Your home address |
| **Inventor citizenship** | United States (or your country) |
| **Entity status** | Micro Entity (if you qualify) or Small Entity |

### Step 5 — Upload the Specification

1. In the document upload section, select **"Specification"** as the document type
2. Upload your PDF
3. Patent Center will show you a preview — confirm it rendered correctly

**Optional but recommended:** Also upload any screenshots or diagrams as **"Drawings"** documents. Good ones to include:
- A screenshot of the intake flow (one question at a time)
- A screenshot of the direction review screen
- A screenshot of the results page with reaction buttons
- A simple flowchart of the multi-round journey (can be hand-drawn and photographed)

### Step 6 — Review the Application Data Sheet (ADS)

Patent Center auto-generates an ADS from what you entered. Review it:
- Confirm inventor name, address, and citizenship are correct
- Confirm entity status is correct
- Confirm the title matches exactly

### Step 7 — Calculate and Pay the Fee

Patent Center will calculate your fee based on entity status:
- **Micro Entity:** ~$160
- **Small Entity:** ~$320

Payment methods accepted: credit card, EFT, deposit account.

Click **"Pay"** and complete payment.

### Step 8 — Submit and Save Your Receipt

After payment, USPTO will issue:
- A **Confirmation Number** — save this immediately
- An **Application Number** — this is your provisional application number (format: 63/XXX,XXX)
- A **Filing Date** — this is your official priority date 🎉

**Save all of this.** Screenshot the confirmation page. You'll need the application number when you file the non-provisional within 12 months.

---

## After Filing

### You Can Now Say "Patent Pending"
Once filed, you may legally label NamEngine as **"Patent Pending"** in marketing materials, on the website, and in investor conversations.

### Set a 12-Month Reminder
Your non-provisional must be filed within **12 months of today's filing date** to claim this priority date. Set a calendar reminder for **2027-08-01** (one month before the deadline) to ensure you have time to work with a patent attorney on the full application.

### Consider a Patent Attorney for the Non-Provisional
The non-provisional application requires formal patent claims, an oath/declaration, and is examined by a USPTO examiner. The indicative claims in the provisional are a starting point, but a registered patent attorney (or agent) will strengthen claim scope, handle examiner responses (office actions), and maximize what the patent actually protects. Estimated cost for a non-provisional with attorney: $5,000–$15,000 depending on complexity.

### Keep Building and Documenting
Your provisional protects everything described in it as of the filing date. If you add significant new features after filing, those additions are NOT protected by this provisional. Document new innovations and consider whether a continuation or new provisional is warranted.

---

## Key Dates and Numbers to Track

| Item | Value |
|---|---|
| Provisional filing date | _(fill in after filing)_ |
| Application number | _(fill in after filing)_ |
| Confirmation number | _(fill in after filing)_ |
| Non-provisional deadline | _(filing date + 12 months)_ |
| Non-provisional attorney reminder | _(filing date + 11 months)_ |

---

## Frequently Asked Questions

**Do I need a patent attorney to file a provisional?**  
No. Provisional applications can be self-filed and do not require an attorney. The non-provisional is where attorney involvement becomes strongly recommended.

**What if I forgot to include something?**  
You cannot amend a provisional after filing. If you realize you missed something significant, you can file a second provisional. The earliest priority date applies to what was included in that provisional.

**Can I still file if the product is already live?**  
Yes. In the US, you have a 1-year grace period after public disclosure to file. NamEngine is live as of 2026-09-08, so you have until approximately 2027-09-08 to file and still claim it. Filing now is still the right move — it maximizes your priority date.

**What does "patent pending" protect?**  
Nothing legally, by itself — you can't sue anyone during the provisional period. But it signals to investors, partners, and competitors that IP protection is in progress, and it establishes your priority date against future filers claiming the same invention.

**Is this international?**  
A US provisional only establishes a US priority date. To protect internationally, you'd file a PCT (Patent Cooperation Treaty) application within 12 months of the provisional, which extends to 150+ countries. Discuss with an attorney if international protection matters for NamEngine.
