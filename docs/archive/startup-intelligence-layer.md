High-Value Use Cases:

| Use Case              | Pain Point                                        | What Greg Could Do                                               |
|-----------------------|---------------------------------------------------|------------------------------------------------------------------|
| Investor update prep  | "What did I tell investors last quarter?"         | Search past updates, ensure consistency, track metrics over time |
| Due diligence prep    | Scrambling to find docs when term sheet arrives   | Index everything, answer DD questions instantly                  |
| Cap table questions   | "What's our option pool after the SAFE converts?" | Parse SAFEs, term sheets, answer scenario questions              |
| Board meeting prep    | Digging through emails and docs for updates       | Summarize progress since last board meeting                      |
| Fundraising narrative | "Does my deck match what's in our data room?"     | Cross-reference pitch claims against actual docs                 |

The killer feature might be: Founders forget what they agreed to. SAFEs, advisor agreements, employee contracts - they're signed and forgotten. Then a question
comes up 18 months later.

"What's the vesting cliff for my CTO?"
"Do our SAFEs have MFN clauses?"
"What did we promise our lead investor about board seats?"

Most realistic MVP:
Upload your docs → ask questions in plain English → get answers with source citations

That alone is valuable. Classification, extraction, and comparison are enhancements once the core works well.

Who'd pay: Founders raising Series A+ (have enough docs to matter, have money, facing DD). Pre-seed founders have 3 docs in a Google Drive folder.

Realistic options for generating training data:

1. Synthetic Generation (Most Practical)

Use GPT-4/Claude to generate realistic docs:

"Generate a SAFE agreement for a $500K investment at a $10M cap
with MFN clause and pro-rata rights. Use realistic names and terms."

You can generate hundreds of variations:

- Different valuations, amounts, terms
- With/without MFN, pro-rata, board seats
- Different stages (pre-seed vs seed vs A)

2. Public Sources

| Source               | What's There                                      |
|----------------------|---------------------------------------------------|
| Y Combinator         | Standard SAFE templates, sample docs              |
| Clerky/Stripe Atlas  | Template legal docs                               |
| SEC EDGAR            | Actual S-1 filings (real term sheets in exhibits) |
| Crunchbase/PitchBook | Funding data (not full docs, but terms)           |
| AngelList templates  | Standardized docs                                 |
| GitHub repos         | Some founders open-source their docs              |

3. Your Own Experience

You've worked at startups - you know what these docs look like and what questions come up. That domain knowledge is actually rare. You can:

- Write realistic scenarios
- Know which questions founders actually ask
- Evaluate if answers make sense

4. Hybrid Approach (Recommended)

1. Start with public templates (SAFEs, term sheets)
2. Use GPT to generate variations with realistic details
3. Manually review ~50 to ensure quality
4. Write questions YOU would ask as a founder
5. Label correct answers yourself

The evaluation set matters most - you need maybe 20-50 high-quality Q&A pairs where you KNOW the right answer. The training data can be noisier and larger.

Your unfair advantage: You understand the domain. Most ML people don't know what a pro-rata right is.
