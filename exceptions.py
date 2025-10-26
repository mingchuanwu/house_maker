"""
Custom exceptions for HouseMaker project
"""


class HouseMakerError(Exception):
    """Base exception for all HouseMaker errors"""
    pass


class ValidationError(HouseMakerError):
    """Raised when input parameters fail validation"""
    
    def __init__(self, parameter_name: str, value, message: str = None):
        self.parameter_name = parameter_name
        self.value = value
        if message:
            self.message = message
        else:
            self.message = f"Invalid value for {parameter_name}: {value}"
        super().__init__(self.message)


class GeometryError(HouseMakerError):
    """Raised when geometric calculations fail or produce invalid results"""
    
    def __init__(self, operation: str, message: str):
        self.operation = operation
        self.message = f"Geometry error in {operation}: {message}"
        super().__init__(self.message)


class DimensionError(ValidationError):
    """Raised when dimensions are outside valid ranges"""
    
    def __init__(self, parameter_name: str, value: float, min_val: float = None, max_val: float = None):
        if min_val is not None and max_val is not None:
            message = f"{parameter_name} ({value}) must be between {min_val} and {max_val}"
        elif min_val is not None:
            message = f"{parameter_name} ({value}) must be at least {min_val}"
        elif max_val is not None:
            message = f"{parameter_name} ({value}) must be no more than {max_val}"
        else:
            message = f"Invalid dimension for {parameter_name}: {value}"
        
        super().__init__(parameter_name, value, message)


class FingerJointError(HouseMakerError):
    """Raised when finger joint calculations fail"""
    
    def __init__(self, message: str):
        self.message = f"Finger joint error: {message}"
        super().__init__(self.message)


class SVGGenerationError(HouseMakerError):
    """Raised when SVG generation fails"""
    
    def __init__(self, component: str, message: str):
        self.component = component
        self.message = f"SVG generation error for {component}: {message}"
        super().__init__(self.message)