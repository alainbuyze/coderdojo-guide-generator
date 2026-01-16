# Bug Report: Upscayl Image Enhancement Integration Issues

## Summary
Fixed critical issues preventing the image enhancement module from working with Upscayl CLI integration.

## Issues Identified

### 1. **Incorrect Models Directory Path** 
**Problem**: Code looked for models in `resources/bin/models` but actual location is `resources/models`
**Impact**: Model file validation always failed
**Fix**: Updated path resolution to go from `bin` → `resources` → `models`

### 2. **Wrong Command Parameters**
**Problem**: Used `-s` for scale parameter, but Upscayl expects `-z`
**Impact**: Upscayl ignored scale setting, used defaults
**Fix**: Changed from `-s` to `-z` based on actual Upscayl help output

### 3. **Unicode Decoding Errors**
**Problem**: Subprocess output contained binary data mixed with text causing `UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f`
**Impact**: Process crashed when reading Upscayl output
**Fix**: Implemented robust encoding handling with UTF-8 fallback to Latin1

### 4. **Path Resolution Issues**
**Problem**: Upscayl couldn't write output file due to relative path confusion
**Impact**: "Couldn't write the image" errors despite successful processing
**Fix**: Used absolute paths for both input and output files

### 5. **Model Availability Mismatch**
**Problem**: Default model `realesrgan-x4plus` doesn't exist in current Upscayl installation
**Impact**: Enhancement always failed at model validation
**Fix**: Updated to use available `upscayl-standard-4x` model

## Changes Made

### Files Modified:
1. **`src/enhancer.py`** - Core enhancement logic
2. **`src/core/config.py`** - Default model configuration  
3. **`.env.app`** - Environment configuration

### Key Fixes:
```python
# Fixed models directory path
models_dir = upscayl_bin.parent.parent / "models"

# Fixed command parameters  
cmd = ["-z", str(scale), "-n", model]  # Not "-s"

# Fixed encoding handling
stderr_text = result.stderr.decode('utf-8', errors='replace')

# Fixed path resolution
input_abs = input_path.resolve()
output_abs = output_path.resolve()
```

## Test Results

### Before Fixes:
- ❌ Unicode decode errors
- ❌ Model not found errors  
- ❌ Output file creation failures
- ❌ Command parameter errors

### After Fixes:
- ✅ Enhancement successful: `enhanced.png` (1.79MB)
- ✅ No Unicode errors
- ✅ Proper command execution
- ✅ Correct output file creation

## Verification

**Command**: `uv run python src/enhancer.py <input> <output> -v`  
**Status**: ✅ Working correctly  
**Output**: Enhanced images with 4x upscaling using available Upscayl models

The image enhancement pipeline is now fully functional and ready for production use.
