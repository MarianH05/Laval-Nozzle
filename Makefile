CASE ?= cases/choked

.PHONY: help \
	run-subsonic run-choked run-internal-shock \
	validate validate-all validate-mesh-study \
	report clean-safe

help:
	@echo "Usage:"
	@echo "  make run-subsonic          # run the subsonic OpenFOAM case"
	@echo "  make run-choked            # run the choked OpenFOAM case"
	@echo "  make run-internal-shock    # run the internal-shock OpenFOAM case"
	@echo "  make validate CASE=...     # validate one existing case without running rhoCentralFoam"
	@echo "  make validate-all          # validate all completed primary cases from existing outputs"
	@echo "  make validate-mesh-study   # run mesh-study post-processing from existing outputs"
	@echo "  make report                # compile report/laval_nozzle_report.pdf"
	@echo "  make clean-safe            # remove only safe temporary files"
	@echo ""
	@echo "Result deletion is intentionally separate: use ./AllcleanResults and confirm DELETE_RESULTS."

run-subsonic:
	./Allrun cases/subsonic

run-choked:
	./Allrun cases/choked

run-internal-shock:
	./Allrun cases/internal_shock

validate:
	./Allvalidate $(CASE)

validate-all:
	python3 scripts/validate_completed_cases.py
	python3 scripts/advanced_validation.py

validate-mesh-study:
	python3 scripts/mesh_independence.py

report:
	cd report && pdflatex -interaction=nonstopmode -halt-on-error laval_nozzle_report.tex
	cd report && pdflatex -interaction=nonstopmode -halt-on-error laval_nozzle_report.tex

clean-safe:
	./Allclean
