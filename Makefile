CASE ?= cases/choked

.PHONY: help run clean validate validate-all advanced report

help:
	@echo "Usage:"
	@echo "  make run CASE=cases/choked        # run blockMesh, checkMesh, rhoCentralFoam, then validate"
	@echo "  make validate CASE=cases/choked   # validate one existing case; may regenerate mesh/checkMesh if needed"
	@echo "  make validate-all                 # aggregate completed-case validation from existing outputs"
	@echo "  make advanced                     # advanced area-Mach and time-history validation"
	@echo "  make report                       # compile report/laval_nozzle_report.pdf"
	@echo "  make clean CASE=cases/choked      # remove generated outputs for one case"

run:
	./Allrun $(CASE)

clean:
	./Allclean $(CASE)

validate:
	./Allvalidate $(CASE)

validate-all:
	python3 scripts/validate_completed_cases.py

advanced:
	python3 scripts/advanced_validation.py

report:
	cd report && pdflatex -interaction=nonstopmode -halt-on-error laval_nozzle_report.tex
	cd report && pdflatex -interaction=nonstopmode -halt-on-error laval_nozzle_report.tex
