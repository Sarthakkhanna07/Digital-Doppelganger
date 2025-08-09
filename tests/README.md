# Time Capsule AI - Test Suite

This directory contains all tests and demos for Time Capsule AI.

## 🧪 Test Files

### `test_comprehensive.py`
**Comprehensive functionality testing**
- Tests all core components (NLP, emotion analysis, database, etc.)
- Validates complete reminder workflow
- Checks tone management and timeline functionality
- **Usage:** `python tests/test_comprehensive.py`
- **Expected:** 100% pass rate (17/17 tests)

### `test_automatic_delivery.py`
**Automatic reminder delivery testing**
- Tests background scheduler functionality
- Validates automatic reminder delivery
- Shows console delivery in action
- **Usage:** `python tests/test_automatic_delivery.py`
- **Options:** 
  - `1` - Run 5-minute automatic demo
  - `2` - Manual trigger test (immediate)
  - `3` - Both

### `demo_user_experience.py`
**User experience demonstration**
- Shows exactly what users receive in WhatsApp
- Demonstrates complete user flow
- Validates emotional context recreation
- **Usage:** `python tests/demo_user_experience.py`
- **Output:** Simulated WhatsApp messages

### `run_all_tests.py`
**Complete test suite runner**
- Runs all tests in correct order
- Provides comprehensive summary
- Handles cleanup automatically
- **Usage:** `python tests/run_all_tests.py`
- **Recommended:** Use this for full validation

## 🚀 Quick Start

### Run All Tests (Recommended)
```bash
python tests/run_all_tests.py
```

### Run Individual Tests
```bash
# Core functionality
python tests/test_comprehensive.py

# Automatic delivery
python tests/test_automatic_delivery.py

# User experience
python tests/demo_user_experience.py
```

## 📊 Expected Results

### ✅ All Tests Passing
When everything works correctly, you should see:
- **Comprehensive Tests:** 17/17 passed (100%)
- **Automatic Delivery:** Reminders delivered with emotional context
- **User Experience:** Realistic WhatsApp message simulation

### 🎯 What Gets Tested

1. **Database Operations**
   - User creation and management
   - Reminder storage and retrieval
   - Timeline entry management

2. **Natural Language Processing**
   - Intent detection for reminders
   - Temporal parsing (tomorrow, Friday, etc.)
   - Activity context extraction

3. **Emotion Analysis**
   - Emotion detection (stress, excitement, etc.)
   - Intensity measurement
   - Context-aware analysis

4. **Automatic Delivery**
   - Background scheduler operation
   - Due reminder detection
   - Rich context recreation
   - Multiple delivery methods

5. **Tone Management**
   - User profile building
   - Response tone adaptation
   - Personalization learning

6. **Timeline Functionality**
   - Entry creation and storage
   - Full-text search capabilities
   - Emotional context preservation

## 🔧 Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Make sure you're in the project root
cd /path/to/time-capsule-ai
python tests/test_comprehensive.py
```

**Database Errors:**
- Tests create temporary databases in `tests/` directory
- Cleanup happens automatically
- If issues persist, manually delete `tests/*.db` files

**Missing Dependencies:**
```bash
pip install -r requirements.txt
```

### Test Database Files
Tests create temporary databases:
- `tests/test_time_capsule.db` - Comprehensive tests
- `tests/test_delivery.db` - Automatic delivery tests  
- `tests/demo_user_experience.db` - User experience demo

These are automatically cleaned up after tests complete.

## 📈 Performance Expectations

- **Comprehensive Tests:** ~30-60 seconds
- **Automatic Delivery:** ~10-30 seconds (immediate mode)
- **User Experience Demo:** ~15-30 seconds
- **Full Test Suite:** ~2-3 minutes

## 🎯 Success Criteria

Your Time Capsule AI is ready for production when:
- ✅ All comprehensive tests pass (17/17)
- ✅ Automatic delivery works with emotional context
- ✅ User experience demo shows realistic WhatsApp messages
- ✅ No database or import errors
- ✅ Full test suite completes successfully

## 🚀 Next Steps

After all tests pass:
1. **Start the main server:** `python main.py`
2. **Connect to Puch AI:** Follow setup instructions in main README
3. **Test with real users:** Create actual reminders via MCP tools
4. **Monitor automatic delivery:** Check console for delivered reminders

---

**Need help?** Check the main README.md or run `python tests/run_all_tests.py` for comprehensive validation.