# The Disaster Response Preparedness Index (DRPI) — Component Specification

**Status:** Proposed framework. This is a specification for adoption and future implementation, not a deployed system. The DRPI is grounded in the empirical data-availability analysis published in:

> Anaya Hernández, A. de J. (2026). *Assessing Data Availability across Maker Networks: Measuring Information Preparedness for Disaster Response.* Fab26 Research Papers Stream, Cambridge, MA, 27–31 July 2026.

Each component below answers a deficiency measured in that study. The tier structure and coverage results reported there are reproducible claims about the world; the DRPI is a design whose usefulness remains to be demonstrated through implementation and validation (see the paper's Future Research).

**Scope note.** The DRPI measures *information readiness* — the depth, currency, and semantic completeness of a facility's data — as a necessary precondition for activating distributed manufacturing in a disaster response scenario. It does not measure physical readiness; complete data cannot by itself confirm that machines are functional, materials in stock, or staff available.

---

## Component 1 — Shared taxonomy for data classification

The 20-class, manufacturing-centric semantic taxonomy developed in the study, mapping disparate source headers to a unified schema:

*Compliance, Contact, Coordinates, Description, Equipment, FacilityAccess, FacilityMetrics, Identifier, JobPosting, Location, ManufacturingProcess, Material, Media, OnlinePresence, OperationalStatus, Organization, Product, RegionalLocation, Schedule, collectionMetadata.*

The taxonomy establishes the minimum baseline — **Identifier, Coordinates, OnlinePresence** — required for robust record linkage across heterogeneous platforms, and deliberately distinguishes *Coordinates*, *Location* (address), and *RegionalLocation*, because precise coordinates carry the highest data-augmentation utility (coordinates can be reverse-geocoded into addresses; addresses geocoded into coordinates). Classification mappings and the validation pipeline are published in this repository's notebooks.

## Component 2 — Baseline open-hardware registry

A curated selection of open-source hardware designs used to benchmark operational capabilities and field readiness *by inference*: open-hardware designs inherently contain implicit metadata about the machinery, processes, and materials required to manufacture their parts, so a facility that demonstrably can build a given design reveals a defined capability set without a full survey. The registry is maintained in [`BENCHMARK_REGISTRY.md`](./BENCHMARK_REGISTRY.md).

## Component 3 — Baseline machinery classification

A standardized fabrication-potential assessment using technical specifications from the Catalogue of Machinery (Anaya Hernández & Internet of Production Alliance, 2023; https://github.com/iop-alliance/okw_machines_catalog), providing a formal framework for identifying the readiness of 3D printers, CNC machinery, and laser-cutting systems within the network.

## Component 4 — Baseline materials registry

A parameterized registry of raw materials — polymers, metals, elastomers — integrated with open-hardware metadata, enabling systematic verification of manufacturing feasibility for critical emergency supplies across distributed production nodes.

## Component 5 — Core technical requirements for facility autonomy

The integration of solar or gas power generation and a comprehensive suite of offline open-source software, ensuring functional autonomy for digital design and machining orchestration during local infrastructure failures. Facility records should capture autonomy indicators explicitly (e.g., backup power generation, offline server capability, uninterruptible power supply availability) — field types the study found in exactly one of ten surveyed platforms.

## Component 6 — Index quantization and calculation

A multi-dimensional assessment applying a five-point segmented scoring methodology to verified baseline requirements (Components 1–5), evaluating preparedness at the level of individual facilities, localized clusters, or global networks. The scoring design must incorporate validation metadata: the study's forensic analysis of crisis-time field collection showed that adherence to a data standard does not by itself ensure data integrity, so verification status is a scoring dimension, not an assumption.

## Component 7 — Essential data prioritization

The eight essential semantic categories validated in the study — **Identifier, Coordinates, OnlinePresence, Contact, ManufacturingProcess, Equipment, Material, Product** — constitute the primary entry requirements for facilities seeking indexing and integration within a resilient manufacturing network. They operationalize the four tasks a disaster-response coordinator must complete against a facility record: *find* it (Identifier, Coordinates), *reach* it (OnlinePresence, Contact), and *task* it (ManufacturingProcess, Equipment, Material, Product); the fourth task, *trust*, requires the validation metadata addressed in Component 6. Because these tasks are conjunctive, a registration-only record contributes no operational value: coverage of all eight categories is the completion criterion, not a quality gradient.

---

## Implementation path

The reference implementation instrument is the **Distributed Manufacturing Data Kit (DMDK)**, the open ETL pipeline in this repository, which currently supports ingestion, harmonization, taxonomical classification, and visualisation across ten heterogeneous platforms. Transitioning the DMDK from a research instrument to a public-facing DRPI data provider — continuous ingestion, automated index recalculation, accessible outputs — is the immediate engineering objective identified in the paper's Future Research, alongside AI-assisted taxonomical classification and point-of-ingestion validation.

## Provenance and independence note

The Open-Know-Where (OKW) standard and its most complete implementation in the study's sample originate from an initiative the author led until January 2025. The study's finding that this source is the sample's most complete reflects internal consistency, not independent validation; validation of the DRPI by parties without prior involvement in the initiative is an explicitly open task.
