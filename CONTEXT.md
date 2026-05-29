# Football Intelligence

This context describes the football intelligence product language: predictions are a core capability, but the product is an agent that answers football questions using data, predictions, and reasoning.

## Language

**Football Intelligence Agent**:
The user-facing assistant that answers natural-language football questions using the project's data, predictions, and analysis.
_Avoid_: Chatbot, FootballPredictor

**Analyst Agent**:
A read-only **Football Intelligence Agent** that answers questions from trusted football data without changing that data.
_Avoid_: Operator agent, automation agent

**Natural-Language Football Question**:
A user question about football matches, teams, predictions, odds, or form expressed in ordinary language.
_Avoid_: Command, job request

**Analyst Tool**:
A read-only football capability the **Analyst Agent** can use to answer a **Natural-Language Football Question**.
_Avoid_: SQL query, chatbot function

**Prediction**:
An estimated football match outcome with probabilities produced by the model.
_Avoid_: Tip, pick

**Upcoming Match**:
A scheduled football match whose final result is not yet known.
_Avoid_: Future match

**Completed Match**:
A football match whose final result is known.
_Avoid_: Past match

**Historical Feature Set**:
The match features derived from **Completed Matches** and used to learn or evaluate prediction behaviour.
_Avoid_: Training features, for-training data

**Future Feature Set**:
The match features derived from **Upcoming Matches** and used to produce **Predictions**.
_Avoid_: Inference features, for-inferencing data

**Match Intelligence Lifecycle**:
The progression where an **Upcoming Match** receives a **Prediction**, becomes a **Completed Match**, and then contributes to later prediction behaviour through the **Historical Feature Set**.
_Avoid_: Daily pipeline, scheduler flow

**Prediction Refresh**:
A run of the **Match Intelligence Lifecycle** that updates match data, feature sets, predictions, and odds without training a new model.
_Avoid_: Retraining, scheduler run

**Source Data Ingestion**:
The activity that brings external football source data into the system for the **Match Intelligence Lifecycle**.
_Avoid_: Scraping, data scraping

**Model Training**:
The explicit activity that learns a new prediction model from the **Historical Feature Set**.
_Avoid_: Prediction refresh

**Football Data Status**:
A read-only snapshot of whether the football data is fresh and complete enough to trust current **Predictions** and odds analysis.
_Avoid_: Health check, job status

**Market Value Signal**:
A research signal where a **Prediction** assigns a higher outcome probability than the betting market implies through available odds.
_Avoid_: Betting tip, guaranteed pick

**Prediction Board**:
A read-only view of **Upcoming Matches**, **Predictions**, odds freshness, and **Market Value Signals** for a chosen date window.
_Avoid_: Tonight, tips board

**Paper Stake**:
A hypothetical stake size used to study a **Market Value Signal** without presenting it as betting advice.
_Avoid_: Recommended stake, betting instruction

**Feature Snapshot**:
A read-only summary of the model inputs and market context used to inspect a **Prediction** or **Market Value Signal**.
_Avoid_: Explanation, reasoning trace

## Relationships

- An **Analyst Agent** is a kind of **Football Intelligence Agent**.
- An **Analyst Agent** answers **Natural-Language Football Questions**.
- An **Analyst Agent** uses **Analyst Tools** to gather football facts.
- A **Football Intelligence Agent** can use one or more **Predictions** when answering a user.
- A **Prediction** is made for an **Upcoming Match**.
- A **Completed Match** can become part of the **Historical Feature Set**.
- A **Future Feature Set** is produced from **Upcoming Matches**.
- The **Match Intelligence Lifecycle** moves football data from **Upcoming Match** to **Prediction** to **Completed Match** to **Historical Feature Set**.
- A **Prediction Refresh** uses the current model to create **Predictions**.
- **Source Data Ingestion** supplies football source data for a **Prediction Refresh**.
- **Model Training** produces a new model from the **Historical Feature Set**.
- **Football Data Status** summarizes the current readiness of source data, feature sets, **Predictions**, and odds analysis.
- A **Market Value Signal** compares a **Prediction** with available odds for the same **Upcoming Match**.
- A **Prediction Board** presents **Predictions** and **Market Value Signals** for **Upcoming Matches** in a date window.
- A **Paper Stake** can be attached to a **Market Value Signal** as research context.
- A **Feature Snapshot** helps inspect why a **Prediction** or **Market Value Signal** appears on a **Prediction Board**.

## Example Dialogue

> **Dev:** "Should the chatbot own the prediction pipeline?"
> **Domain expert:** "No — the **Football Intelligence Agent** uses **Predictions**, but predictions are only one part of the answer."
>
> **Dev:** "Can the agent refresh the match data if it looks stale?"
> **Domain expert:** "No — the first version is an **Analyst Agent**, so it can answer from data but not change it."
>
> **Dev:** "Should LangChain run the scraping and prediction pipeline?"
> **Domain expert:** "No — LangChain belongs to the **Analyst Agent** answering **Natural-Language Football Questions**."
>
> **Dev:** "Can the agent write arbitrary SQL?"
> **Domain expert:** "No — the **Analyst Agent** should use curated **Analyst Tools** first."
>
> **Dev:** "Once Arsenal vs Man City finishes, is it still part of the prediction input?"
> **Domain expert:** "Yes — it changes from an **Upcoming Match** into a **Completed Match**, then contributes to the **Historical Feature Set** for later **Predictions**."
>
> **Dev:** "Is this just a scheduler job?"
> **Domain expert:** "No — the job runs the **Match Intelligence Lifecycle**; scheduling is only how often it runs."
>
> **Dev:** "When Arsenal vs Man City finishes, do we retrain immediately?"
> **Domain expert:** "No — a **Prediction Refresh** updates the feature state and predictions; **Model Training** is separate."
>
> **Dev:** "Is this still called scraping once it sits inside the product namespace?"
> **Domain expert:** "No — scraping describes the current implementation; the product activity is **Source Data Ingestion**."
>
> **Dev:** "Does status mean checking whether the server is up?"
> **Domain expert:** "No — **Football Data Status** tells us whether the football data is fresh and complete enough to trust today's **Predictions** and odds analysis."
>
> **Dev:** "Is a value pick a betting recommendation?"
> **Domain expert:** "No — a **Market Value Signal** is a research signal comparing model probability with market-implied probability."
>
> **Dev:** "Should tonight's command only show evening kickoffs?"
> **Domain expert:** "No — the casual shortcut can say tonight, but the product concept is a **Prediction Board** for the remaining **Upcoming Matches** in today's local date window."
>
> **Dev:** "Can we show Kelly stake as the recommended bet size?"
> **Domain expert:** "No — until calibration is proven, show it as a **Paper Stake** for research."
>
> **Dev:** "Should 'why this pick?' generate a confident prose explanation?"
> **Domain expert:** "No — v1 should show a grounded **Feature Snapshot** rather than inventing model reasoning."

## Flagged Ambiguities

- "FootballPredictor" describes the old product framing; use **Football Intelligence Agent** for the future product concept.
- "agentic system" could mean an agent that changes system state; resolved for v1 as **Analyst Agent**, which is read-only.
- "LangChain" is an implementation choice for the **Analyst Agent**, not the **Match Intelligence Lifecycle**.
- "chatbot functions" are existing implementation pieces; use **Analyst Tool** for the read-only capabilities exposed to the agent.
- "for training" and "for inferencing" describe implementation usage; resolved as **Historical Feature Set** and **Future Feature Set**.
- "scheduler" describes deployment timing, not the football concept; use **Match Intelligence Lifecycle** for the domain flow.
- "refresh predictions" and "train model" are separate activities; completed matches can update feature state without triggering **Model Training**.
- "scraping" describes the current external API implementation; use **Source Data Ingestion** for the product activity.
- "status" could mean infrastructure health or job state; resolved as **Football Data Status**, a football-data readiness snapshot.
- "value pick" is useful CLI shorthand, but the canonical product concept is **Market Value Signal** because it does not imply betting advice.
- "tonight" is casual command shorthand; use **Prediction Board** for the product view because the date window may include non-evening matches.
- "stake" can imply betting advice; resolved as **Paper Stake** when attached to **Market Value Signals**.
- "why this pick?" can imply generated reasoning; resolved as a **Feature Snapshot** for v1.
