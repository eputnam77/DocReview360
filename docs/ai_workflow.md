# AI in the DocReview360 Workflow

DocReview360 includes lightweight AI helpers that speed up common tasks and keep your projects tidy. The utilities run locally so you can try them without extra services.

## Document insights

Functions in `docuflow.ai_utils` analyse text to suggest document types, detect anomalies and even recommend an export format. When you import or edit a file these helpers provide instant feedback so you know whether the content looks valid.

## Workload balancer

The `ai_balancer` module distributes jobs among workers. It tracks how many tasks each worker has and assigns new ones to the least busy person. This keeps work flowing smoothly even as your team grows.

## Putting it together

You can call these AI helpers from your own scripts or integrate them into a larger workflow. They help you sort incoming documents, flag unusual text and share the load across your team. Together they reduce manual effort and let you focus on writing great content.
