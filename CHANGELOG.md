# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Comprehensive Unit Test Suite**: 164 unit tests covering all core utilities
  - `test_query_utils.py`: Query building and text processing (52 tests)
  - `test_image_utils.py`: Image processing and hashing (31 tests)
  - `test_file_utils.py`: File operations and batching (20 tests)
  - `test_cache.py`: Search and embedding cache (19 tests)
  - `test_search_engine.py`: Search engine abstraction (25 tests)
  - `test_vision_pipeline.py`: Vision pipeline logic (17 tests)
- **UI/UX Improvements**:
  - New navy blue color palette for refined visual appearance
  - Refined accent colors (electric blue `#2a7ef5`)
  - Improved checkbox layout in intention selector
  - Enhanced animations: card cascade, dropdown pop, checkbox pop, status fade
- **Bug Fixes**:
  - Fixed z-index stacking conflict where "Intention" label overlapped dropdown menu
  - Improved checkbox centering with flexbox layout
  - Better hover states and visual feedback

### Changed
- **CSS Redesign**:
  - Complete color palette overhaul (navy blue theme)
  - New CSS variables for consistent theming
  - Improved spacing and alignment (8px gaps instead of 6px)
  - Better responsive behavior
- **Checkbox Styling**:
  - Increased min-height from 34px to 36px
  - Improved label ellipsis handling
  - Better tooltip positioning with `flex-shrink: 0`

### Technical
- Pytest integration for unit testing
- pytest-cov for coverage tracking
- No breaking changes to existing functionality

---

## [Previous versions]

For earlier changes, see git history.
