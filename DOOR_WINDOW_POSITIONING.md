# Door and Window Positioning Enhancements

## Overview
This document describes the enhancements made to door and window positioning in the HouseMaker system, including multi-floor window support and flexible door placement.

## Key Changes

### 1. Multi-Floor Window Positioning

Windows are now automatically distributed across multiple floors for tall houses. The number of floors is calculated using:

```python
floor_height = (house_length + house_width) / 2
num_floors = house_height // floor_height  # Minimum 1
```

**Example:**
- House: 80mm × 80mm × 240mm
- Floor height: (80 + 80) / 2 = 80mm
- Number of floors: 240 // 80 = 3 floors
- Windows will be placed on each floor at appropriate heights

### 2. Ground-Level Door Placement

**Doors are always placed at ground level** regardless of house height. This ensures:
- Realistic architectural design
- Proper entrance accessibility
- Consistent placement at `y = margin` (typically 6mm from bottom)

### 3. Flexible Door Panel Selection

Doors can now be placed on different wall panels:

**Option 1: Front Gable Wall (default)**
```python
house = HouseMaker(
    length=100,
    width=100,
    height=150,
    auto_add_components=True  # Door on gable_wall_front by default
)
```

**Option 2: Side Wall Right**
```python
# Create house without auto components
house = HouseMaker(
    length=100,
    width=100,
    height=150,
    auto_add_components=False
)

# Manually add components with door on side wall
house.architectural_config.add_automatic_components(
    add_windows=True,
    add_doors=True,
    door_panel='side_wall_right'  # Door on side wall
)
```

## Implementation Details

### Modified Files

1. **`architectural_components.py`**
   - Added [`calculate_number_of_floors()`](architectural_components.py:662) method to [`ComponentPositioner`](architectural_components.py:655) class
   - Updated window positioning logic to distribute across floors
   - Enhanced door placement to ensure ground-level positioning

2. **`architectural_config.py`**
   - Added `door_panel` parameter to [`add_automatic_components()`](architectural_config.py:52) method
   - Supports both `'gable_wall_front'` and `'side_wall_right'` options

3. **`__init__.py`**
   - Updated default configuration to use `door_panel='gable_wall_front'`

### Code Changes Summary

```python
class ComponentPositioner:
    def calculate_number_of_floors(self) -> int:
        """Calculate number of floors using formula:
        house_height // ((house_length + house_width)/2)"""
        avg_dimension = (self.house_geometry.x + self.house_geometry.y) / 2
        floor_height = avg_dimension
        num_floors = int(self.house_geometry.z // floor_height)
        return max(1, num_floors)
```

Window positioning now iterates through floors:
```python
num_floors = self.calculate_number_of_floors()
floor_height = self.house_geometry.z / num_floors

for floor in range(num_floors):
    window_y = floor * floor_height + floor_height * 0.4
    # Position window at this height...
```

Door positioning remains at ground level:
```python
door_y = margin  # Always at ground level
```

## Usage Examples

### Example 1: Short House (1 Floor)
```python
house = HouseMaker(length=100, width=100, height=50)
# Floor height: 100mm
# House height: 50mm → 0 floors (minimum 1)
# Result: 1 window per wall at mid-height
```

### Example 2: Medium House (2 Floors)
```python
house = HouseMaker(length=100, width=100, height=150)
# Floor height: 100mm
# House height: 150mm → 1 floor
# Result: 1-2 windows per wall distributed vertically
```

### Example 3: Tall House (3+ Floors)
```python
house = HouseMaker(length=80, width=80, height=240)
# Floor height: 80mm
# House height: 240mm → 3 floors
# Result: Windows on multiple floors (ground, 1st, 2nd)
```

### Example 4: Door on Side Wall
```python
house = HouseMaker(length=100, width=100, height=150, auto_add_components=False)
house.architectural_config.add_automatic_components(
    add_windows=True,
    add_doors=True,
    door_panel='side_wall_right'
)
# Result: Door on right side wall at ground level
```

## Testing

Test files have been generated:
- `test_1floor.svg` - Single floor house (100×100×50mm)
- `test_3floors.svg` - Three floor house (80×80×240mm)

To generate additional test houses:
```bash
python3 generate_house.py --length 100 --width 100 --height 150 --output test.svg
```

## Benefits

1. **Realistic Multi-Story Buildings**: Windows naturally distribute across floors
2. **Proper Door Placement**: Doors always at ground level for realistic entrances
3. **Flexible Design**: Choose door location based on architectural needs
4. **Automatic Scaling**: Window distribution adapts to house height
5. **Collision Avoidance**: Windows avoid doors and maintain proper spacing

## Backward Compatibility

All changes are backward compatible:
- Default behavior unchanged (door on front gable wall)
- Existing code continues to work without modifications
- New features are opt-in via parameters

## Future Enhancements

Possible future improvements:
- Multiple doors (e.g., front and back entrances)
- Balcony/terrace support on upper floors
- Staircase indicators
- Custom floor heights per level
- Window size variation by floor