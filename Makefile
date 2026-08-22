.PHONY: check test compile actions-supply-chain project-check smoke planning-audit challenge-validate challenges harness-version product-version harness-lock harness-eval-validate pi-runtime-check

check:
	python3 tools/harness_check.py

test:
	python3 -m unittest discover -s tests -v

compile:
	python3 -m compileall -q tools tests

actions-supply-chain:
	python3 tools/check_actions_supply_chain.py

project-check:
	python3 tools/run_quality.py

smoke: check actions-supply-chain compile test project-check

planning-audit:
	python3 tools/github_planning.py audit --offline

challenge-validate:
	python3 tools/run_challenges.py

challenges:
	python3 tools/run_challenges.py --run

harness-version:
	python3 tools/harness_upgrade.py status

product-version:
	python3 tools/product_version.py

harness-lock:
	python3 tools/harness_upgrade.py lock --repository stauntonjr/agentic-project-template --release unreleased-v0.4.0-source-snapshot --commit e7dae5f2f5581c6bf1a8a91f8a3c595140d4bc07 --yes

harness-eval-validate:
	python3 tools/evaluate_harness.py

pi-runtime-check:
	python3 tools/pi_adapter_check.py
