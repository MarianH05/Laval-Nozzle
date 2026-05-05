CASE ?= cases/baseline_choked

.PHONY: run clean validate report

run:
	./Allrun $(CASE)

clean:
	./Allclean $(CASE)

validate:
	./Allvalidate $(CASE)

report:
	cd report && pdflatex -interaction=nonstopmode laval_nozzle_report.tex
	cd report && pdflatex -interaction=nonstopmode laval_nozzle_report.tex
