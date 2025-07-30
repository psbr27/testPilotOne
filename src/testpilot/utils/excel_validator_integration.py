"""
Excel Validator Integration Module
Integrates the ExcelDataValidator with the main TestPilot processing logic.
"""

import os
import sys
from pathlib import Path

from ..core.excel_data_validator import ExcelDataValidator
from ..utils.logger import get_logger

logger = get_logger("ExcelValidatorIntegration")


def validate_excel_input(input_file_path: str, 
                        validate_input: bool = True,
                        force_validation: bool = False) -> str:
    """
    Validate Excel input file and return path to validated file.
    
    Args:
        input_file_path: Path to the original Excel file
        validate_input: Whether to perform validation (default: True)
        force_validation: Force validation even if validated file exists
        
    Returns:
        str: Path to the validated Excel file
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If validation fails with too many errors
    """
    if not validate_input:
        logger.debug("Excel validation disabled, using original file")
        return input_file_path
    
    if not os.path.exists(input_file_path):
        raise FileNotFoundError(f"Input Excel file not found: {input_file_path}")
    
    # Generate paths for validated file and summary
    input_path = Path(input_file_path)
    validated_file = input_path.parent / f"{input_path.stem}_validated.xlsx"
    summary_file = input_path.parent / f"{input_path.stem}_validation_summary.txt"
    
    # Check if validated file already exists and is newer than input
    if not force_validation and validated_file.exists():
        input_mtime = os.path.getmtime(input_file_path)
        validated_mtime = os.path.getmtime(validated_file)
        
        if validated_mtime > input_mtime:
            logger.info(f"Using existing validated file: {validated_file}")
            logger.info(f"To force re-validation, delete the validated file or use --force-validation")
            return str(validated_file)
    
    logger.info(f"Validating Excel input file: {input_file_path}")
    
    # Initialize validator and process file
    validator = ExcelDataValidator()
    
    try:
        results = validator.validate_excel_file(
            input_file=input_file_path,
            output_file=str(validated_file),
            summary_file=str(summary_file)
        )
        
        # Log validation results
        logger.info(f"Validation completed:")
        logger.info(f"  Total rows: {results['total_rows']}")
        logger.info(f"  Valid rows: {results['valid_rows']}")
        logger.info(f"  Invalid rows: {results['invalid_rows']}")
        logger.info(f"  Validation rate: {results['validation_rate']:.1f}%")
        
        # Check if validation rate is acceptable
        min_validation_rate = 80.0  # Configurable threshold
        if results['validation_rate'] < min_validation_rate:
            logger.warning(
                f"Low validation rate ({results['validation_rate']:.1f}%) - "
                f"below threshold of {min_validation_rate}%"
            )
            logger.warning(f"Check validation summary: {summary_file}")
            
            # Could add option to proceed or fail based on validation rate
            # For now, we proceed with a warning
        
        if results['invalid_rows'] > 0:
            logger.warning(f"{results['invalid_rows']} rows failed validation")
            logger.warning(f"These tests will be skipped during execution")
            logger.info(f"See details in: {summary_file}")
        
        logger.info(f"Validated Excel file saved: {validated_file}")
        return str(validated_file)
        
    except Exception as e:
        logger.error(f"Excel validation failed: {e}")
        logger.error("Falling back to original file")
        return input_file_path


def add_validation_args(parser):
    """
    Add Excel validation arguments to argument parser.
    
    Args:
        parser: argparse.ArgumentParser instance
    """
    validation_group = parser.add_argument_group('Excel Validation Options')
    
    validation_group.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip Excel input validation and use original file as-is'
    )
    
    validation_group.add_argument(
        '--force-validation',
        action='store_true', 
        help='Force Excel validation even if validated file already exists'
    )
    
    validation_group.add_argument(
        '--validation-threshold',
        type=float,
        default=80.0,
        help='Minimum validation rate percentage to proceed (default: 80.0)'
    )


def get_validation_status_summary(input_file_path: str) -> dict:
    """
    Get a summary of validation status for an Excel file.
    
    Args:
        input_file_path: Path to the original Excel file
        
    Returns:
        dict: Validation status information
    """
    input_path = Path(input_file_path)
    validated_file = input_path.parent / f"{input_path.stem}_validated.xlsx"
    summary_file = input_path.parent / f"{input_path.stem}_validation_summary.txt"
    
    status = {
        'input_file': input_file_path,
        'validated_file_exists': validated_file.exists(),
        'validated_file_path': str(validated_file),
        'summary_file_exists': summary_file.exists(), 
        'summary_file_path': str(summary_file),
        'needs_validation': True
    }
    
    if validated_file.exists() and os.path.exists(input_file_path):
        input_mtime = os.path.getmtime(input_file_path)
        validated_mtime = os.path.getmtime(validated_file)
        status['needs_validation'] = validated_mtime <= input_mtime
        status['validation_age_seconds'] = input_mtime - validated_mtime
    
    return status