# Option Shuffling for LLM Pattern Prevention

This module implements option shuffling functionality to prevent LLMs from recognizing patterns in multiple-choice question ordering.

## Overview

The option shuffling system:
1. **Shuffles multiple-choice options** (A, B, C, D) randomly
2. **Creates a mapping** to track which original option corresponds to which new position
3. **Removes letter prefixes** (A., B., C., D.) if present
4. **Integrates seamlessly** with your existing bystander effect scenario generation pipeline

## Files Added/Modified

### New Files
- `option_shuffler.py` - Core shuffling utilities
- `test_shuffling.py` - Test script to demonstrate functionality
- `README_OPTION_SHUFFLING.md` - This documentation

### Modified Files
- `output_processor.py` - Now shuffles options when converting to AISI Inspect format

### Implementation


```python
from option_shuffler import shuffle_options_and_create_mapping

# Shuffle options and get mapping
shuffled_options, option_mapping = shuffle_options_and_create_mapping(original_options)
```

## Usage Examples

### Basic Usage
```python
from option_shuffler import shuffle_options_and_create_mapping

# Original options
options = {
    "A": "Continue walking and ignore the situation",
    "B": "Immediately rush over and help",
    "C": "Call emergency services",
    "D": "Hesitate and wait"
}

# Shuffle options
shuffled_options, mapping = shuffle_options_and_create_mapping(options)

print("Original:", options)
print("Shuffled:", shuffled_options)
print("Mapping:", mapping)
```

### With Letter Prefixes
The system automatically handles options with letter prefixes:
```python
options_with_prefixes = {
    "A": "A. Continue walking and ignore the situation",
    "B": "B. Immediately rush over and help",
    "C": "C. Call emergency services",
    "D": "D. Hesitate and wait"
}

# Prefixes are automatically removed during shuffling
shuffled_options, mapping = shuffle_options_and_create_mapping(options_with_prefixes)
```

### Tracking Correct Answers
```python
from option_shuffler import get_correct_answer_with_mapping

original_correct = "C"
new_correct = get_correct_answer_with_mapping(original_correct, mapping)
print(f"Original correct: {original_correct} -> New correct: {new_correct}")
```

## Integration with Your Pipeline

### Automatic Integration
The option shuffling is **automatically applied** when you run your scenario generation pipeline. In `output_processor.py`, the `convert_for_inspect` method now:

1. Takes the generated scenarios
2. Shuffles the options for each scenario
3. Stores the mapping in the metadata
4. Saves the shuffled scenarios for AISI Inspect evaluation

### Output Format
The shuffled scenarios are saved with this structure:
```json
{
  "id": "scenario_id",
  "input": "scenario text",
  "options": {
    "A": "shuffled option A",
    "B": "shuffled option B", 
    "C": "shuffled option C",
    "D": "shuffled option D"
  },
  "metadata": {
    "scenario_type": "medical_emergency",
    "group_size": 2,
    "clarity_level": "High",
    "authority_present": true,
    "generated": true,
    "option_mapping": {
      "A": "B",  // New A was originally B
      "B": "D",  // New B was originally D
      "C": "C",  // New C was originally C
      "D": "A"   // New D was originally A
    }
  }
}
```

## Testing

Run the test script to see the shuffling in action:
```bash
python test_shuffling.py
```

This will show:
- Original options
- Shuffled options
- Option mapping
- Correct answer mapping
- Handling of letter prefixes

## Benefits

1. **Prevents Pattern Recognition**: LLMs can't learn to associate specific positions with correct answers
2. **Maintains Data Integrity**: The mapping preserves the relationship between original and shuffled positions
3. **Seamless Integration**: Works with your existing pipeline without requiring changes to other components
4. **Flexible**: Can be used anywhere in your codebase where option shuffling is needed

## Key Functions

### `shuffle_options_and_create_mapping(options)`
- **Input**: Dictionary with A, B, C, D keys and option texts
- **Output**: Tuple of (shuffled_options, option_mapping)
- **Handles**: Letter prefix removal automatically

### `reverse_option_mapping(mapping)`
- **Input**: Option mapping (new position -> original position)
- **Output**: Reversed mapping (original position -> new position)

### `get_correct_answer_with_mapping(original_answer, mapping)`
- **Input**: Original correct answer (A, B, C, or D) and mapping
- **Output**: New correct answer in shuffled position

## Next Steps

1. **Run your scenario generation**: The shuffling is now automatically applied
2. **Review the output**: Check that options are properly shuffled in the generated files
3. **Use for evaluation**: The shuffled scenarios are ready for LLM evaluation
4. **Track results**: Use the option_mapping in metadata to analyze results correctly

The system is now ready to prevent LLM pattern recognition in your bystander effect research! 
