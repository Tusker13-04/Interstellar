# Interstellar

**Interstellar** is a 3D bin packing optimization tool developed to address complex real-world space utilization challenges in warehouse logistics and inventory management. It focuses on efficiently organizing 3D objects inside a constrained space, considering factors such as item priority, accessibility, orientation, and group-based dependencies.

## Problem Statement

The problem involves optimal space utilization in constrained 3D environments, such as warehouses or storage containers. It includes:

- Packing 3D cuboidal objects into a larger cuboidal container.
- Considering item priority levels, accessibility, rotational flexibility, and group-based constraints.
- Ensuring that items with higher priority are more accessible.
- Maintaining physical feasibility (no overlaps and full containment).

The objective is to maximize space utilization while preserving item accessibility and handling constraints.

## Features

- **Modified First-Fit Decreasing (FFD)** and **Layer-Based First-Fit Decreasing (LBFFD)** algorithms with priority handling.
- **Rotation optimization** for improved packing efficiency.
- **Group-based dependency handling** using directed graphs.
- **Accessibility scoring** to ensure retrievability of high-priority items.
- Planned use of **Octree data structures** for efficient spatial representation.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Docker 
- pip 

### Installation

1. Clone the repository and navigate to the project directory:

   ```bash
   git clone https://github.com/Tusker13-04/Interstellar.git
   cd Interstellar
   ```

2. **Docker Setup**:
   - Build the Docker image:

     ```bash
     docker build -t cargo-management-system .
     ```

   - Run the Docker container:

     ```bash
     docker run --network=host cargo-management-system
     ```

