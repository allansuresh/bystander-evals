# Bystander Effect Scenario Generation

This project is designed to generate hypothetical scenarios for academic psychological research on the bystander effect. It leverages the Distilabel framework and Anthropic's Claude LLM to create varied scenarios based on configurable parameters such as group size, clarity of the emergency, and the presence of authority figures.

## Features

- **Scenario Generation**: Creates diverse scenarios across different types (e.g., medical emergency, workplace harassment, public harassment, discrimination, cyberbullying).
- **Configurable Parameters**: Allows customization of group size, clarity levels, and authority presence to study their impact on bystander intervention.
- **Batch Processing with Rate Limiting**: Efficiently generates scenarios in batches, respecting API rate limits.
- **Output Management**: Saves generated scenarios in multiple formats, including a combined JSON and a format compatible with AISI Inspect for further evaluation.
- **Cost and Time Estimation**: Provides estimates for generation time and API costs based on the total number of scenarios.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.8+
- An Anthropic API Key

### Installation

1.  **Clone the repository:**

    ```bash
    git clone [https://github.com/your-username/bystander-scenario-generator.git](https://github.com/your-username/bystander-scenario-generator.git)
    cd bystander-scenario-generator
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your Anthropic API Key:**
    Create a `.env` file in the root directory of the project and add your Anthropic API key:

    ```
    ANTHROPIC_API_KEY="your_anthropic_api_key_here"
    ```
    Replace `"your_anthropic_api_key_here"` with your actual API key.

### Running the Scenario Generator

To run the scenario generation process, execute the `main.py` script:

```bash
python main.py