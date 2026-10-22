# TaskFlow learning documentation

Start with [the project handbook](TASKFLOW_HANDBOOK.md) or the formatted `TaskFlow_Project_Handbook.docx` in this folder.

For a visual introduction, open the [Archify learning atlas](../archify-learning/index.html). Its four interactive maps explain the application architecture, one task edit, background reminders, and how Archify produces a diagram. A separate [beginner walkthrough](../archify-learning/README.md) provides source-file references and exercises.

The handbook has 25 chapters, from the product idea and basic vocabulary through architecture, data modeling, authentication, frontend behavior, background jobs, testing, deployment, operations, and interviews. It includes an independent feature exercise, an eight-week learning plan, a practical readiness assessment, and 30 technical interview questions with answers grounded in this code.

Suggested reading order:

1. Chapters 1–8: understand and run what already exists.
2. Chapters 9–12: trace requests, frontend state, and reminders.
3. Chapters 13–16: rebuild stages, implement a small feature, and test it.
4. Chapters 17–20: prepare deployment and learn operation/recovery.
5. Chapters 21–24: practice explaining evidence and your own contribution.

The [deployment companion](deployment/README.md) includes standalone Linux server examples. They are separate from the local development Compose stack. Configuration validation does not mean that public DNS, HTTPS, SMTP, backup restoration or a cloud deployment has already been verified. No public infrastructure was created for this documentation.

Exact package versions are in the application lockfiles. The original READMEs remain the quick setup references. Update this handbook whenever the application's contract or deployment process changes.
