## Summary of Changes
Provide a brief summary of the changes introduced in this PR and why they are necessary.

## Subsystems Touched
- [ ] Organization Engine & Role Contracts
- [ ] Task Execution DAG & State Machine
- [ ] Scheduler, Worker Leases & Recovery
- [ ] Decision Intelligence & Counterfactuals
- [ ] Discrete-Event Simulation Engine
- [ ] Scoped Memory & Context Isolation
- [ ] Dashboard & API
- [ ] Documentation / Release Packaging

## Verification & Testing
Describe the tests you ran to verify your changes:
```bash
pytest tests -v --cov=simarch
python examples/first_organization.py
```

## Checklist
- [ ] My code adheres to the project coding style.
- [ ] I have added tests that prove my fix or feature works.
- [ ] No temporary files, test databases, or credentials are committed.
- [ ] All documentation has been updated.
