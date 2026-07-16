# Baseline Open-Hardware Benchmark Registry

**Purpose.** This registry implements Component 2 of the [Disaster Response Preparedness Index specification](./DRPI_SPECIFICATION.md). It lists open-source hardware designs used to benchmark a facility's operational capabilities and field readiness **by inference**: every open-hardware design carries implicit metadata about the machinery, manufacturing processes, and materials required to produce its parts. A facility that demonstrably can build a benchmark design therefore reveals a defined capability set without an exhaustive survey — reducing the collection cost and false-reporting surface that exhaustive surveying incurs, particularly during active crises.

Standards such as Open-Know-Where (OKW) provide the parameterized metadata framework to support this inference-based collection, and matchmaking algorithms using catalog-based string matching can link machinery, processes, and products against the [Catalogue of Machinery](https://github.com/iop-alliance/okw_machines_catalog).

**How to use.** A facility documents a verifiable build of one or more benchmark designs (build log, photos, or serialised output). Each documented build maps to the capability set in the table below and populates the corresponding DRPI essential categories (*ManufacturingProcess, Equipment, Material, Product*) by inference rather than self-declaration.

**Status.** Curated selection, proposed with the DRPI specification; contributions of additional benchmarks are welcome via pull request, subject to the inclusion criteria below.

---

## Registry

### 1. LibreWater — solar desalination

- **Project:** LibreWater (open-source solar water desalination / purification)
- **Readiness dimension:** water access and purification potential
- **Capability set inferred from a verified build:** basic fabrication of watertight assemblies; thermoforming or moulding of food-safe components; solar-thermal assembly; material handling of polymers and sealants
- **Disaster-response relevance:** potable water provision where supply networks are disrupted

### 2. OpenFlexure Microscope — field medical and laboratory equipment

- **Project:** OpenFlexure Microscope (open-source, lab-grade 3D-printed microscope)
- **Readiness dimension:** readiness for field medical and laboratory equipment production
- **Capability set inferred from a verified build:** high-precision FDM 3D printing; fine mechanical assembly; optics handling; basic electronics integration (camera, illumination, motor control); firmware flashing
- **Disaster-response relevance:** diagnostic capacity (e.g., microscopy for infectious-disease fieldwork) in settings cut off from laboratory supply chains

### 3. The Nimble — offline digital infrastructure

- **Project:** The Nimble (compact offline server)
- **Readiness dimension:** offline server resilience and digital infrastructure autonomy
- **Capability set inferred from a verified build:** single-board-computer assembly and configuration; local network deployment; enclosure fabrication; offline content and design-file hosting
- **Disaster-response relevance:** access to design repositories, documentation, and coordination tooling when internet connectivity fails — a precondition for digital fabrication to continue during infrastructure collapse (DRPI Component 5)

### 4. Solar or gas generators — power autonomy

- **Category benchmark** (design-agnostic: any documented open or commercial build/installation qualifies)
- **Readiness dimension:** power supply stability and electrical autonomy
- **Capability set inferred from a verified installation:** electrical assembly and safety practice; power-system sizing; maintenance capacity for autonomous operation
- **Disaster-response relevance:** continued machine operation during grid failure; jointly with benchmark 3, constitutes the facility-autonomy requirement of DRPI Component 5

### 5. PPE manufacturing — health-crisis production transition

- **Category benchmark** (e.g., face shields, mask components, ventilator parts from validated open designs of the COVID-19 response)
- **Readiness dimension:** capacity to transition production to vital protective equipment during health crises
- **Capability set inferred from a verified production run:** rapid retooling; batch 3D printing or laser cutting; garment/textile work where applicable; hygiene-compliant handling and packaging; throughput beyond one-off prototyping
- **Disaster-response relevance:** the empirically proven use case — distributed PPE production was the maker networks' documented pandemic contribution, and remains the reference scenario for the DRPI

---

## Inclusion criteria for new benchmarks

A candidate design qualifies if it is: (1) open source, with complete, buildable documentation; (2) mapped to a distinct readiness dimension not already covered, or a materially different capability set within one; (3) buildable with equipment classes present in the Catalogue of Machinery; and (4) relevant to at least one recurring disaster-response supply need (water, power, medical, shelter, communications, protective equipment).

## Citation

If you use this registry, cite:

> Anaya Hernández, A. de J. (2026). *Assessing Data Availability across Maker Networks: Measuring Information Preparedness for Disaster Response.* Fab26 Research Papers Stream, Cambridge, MA, 27–31 July 2026.
