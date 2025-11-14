# Accessibility Testing Guide - Flavor Quest

This document provides comprehensive instructions for conducting accessibility audits and testing of the Flavor Quest application to ensure it's usable by people with disabilities.

## 📋 Table of Contents

1. [Introduction](#introduction)
2. [WCAG Standards](#wcag-standards)
3. [Automated Testing Tools](#automated-testing-tools)
4. [Manual Testing Procedures](#manual-testing-procedures)
5. [Common Issues & Fixes](#common-issues--fixes)
6. [Testing Checklist](#testing-checklist)
7. [Remediation Guide](#remediation-guide)

---

## 🔍 Introduction

### What is Accessibility?

Web accessibility ensures that websites and applications are usable by everyone, including people with disabilities such as:
- **Visual impairments**: Blindness, low vision, color blindness
- **Hearing impairments**: Deafness, hard of hearing
- **Motor impairments**: Limited fine motor control, tremors
- **Cognitive impairments**: Learning disabilities, attention disorders

### Why Accessibility Matters

- **Legal Compliance**: Required by laws like ADA (Americans with Disabilities Act), AODA (Accessibility for Ontarians with Disabilities Act)
- **Ethical Responsibility**: Ensures equal access to information and services
- **Business Benefits**: Expands user base, improves SEO, better user experience for all
- **Best Practice**: Industry standard for modern web development

### Flavor Quest Application URLs

**Frontend**: `https://flavourquestcap.netlify.app`  
**Backend API**: `https://flavour-quest-e7ho.onrender.com`

---

## 📐 WCAG Standards

### WCAG 2.1 Levels

The Web Content Accessibility Guidelines (WCAG) define three levels of compliance:

#### Level A (Minimum)
- Basic accessibility requirements
- Must be met for legal compliance

#### Level AA (Recommended)
- Enhanced accessibility
- Most common target for compliance
- Required for many organizations

#### Level AAA (Optimal)
- Highest level of accessibility
- Difficult to achieve for all content

### Key WCAG Principles (POUR)

1. **Perceivable**: Information must be presentable to users in ways they can perceive
2. **Operable**: Interface components must be operable
3. **Understandable**: Information and UI operation must be understandable
4. **Robust**: Content must be robust enough for assistive technologies

---

## 🛠️ Automated Testing Tools

### 1. Lighthouse (Chrome DevTools)

**Best for**: Quick automated audits

#### Steps:
1. Open Chrome DevTools (F12)
2. Navigate to **Lighthouse** tab
3. Select **Accessibility** checkbox
4. Click **Generate report**
5. Review accessibility score and issues

#### What it checks:
- Color contrast
- ARIA attributes
- Alt text for images
- Form labels
- Keyboard navigation
- Screen reader compatibility

### 2. WAVE (Web Accessibility Evaluation Tool)

**Best for**: Visual accessibility feedback

#### Steps:
1. Install WAVE browser extension (Chrome/Firefox)
2. Navigate to your application
3. Click WAVE icon in toolbar
4. Review visual overlay of issues
5. Check detailed report

#### What it checks:
- Missing alt text
- Form label issues
- Color contrast
- Heading structure
- ARIA issues
- Link text

**Website**: https://wave.webaim.org/

### 3. axe DevTools

**Best for**: Developer-focused testing

#### Steps:
1. Install axe DevTools extension
2. Open Chrome DevTools
3. Navigate to **axe DevTools** tab
4. Click **Scan** button
5. Review violations and recommendations

#### What it checks:
- WCAG 2.1 Level A, AA compliance
- ARIA implementation
- Keyboard navigation
- Color contrast
- Form accessibility

**Website**: https://www.deque.com/axe/devtools/

### 4. Pa11y (Command Line)

**Best for**: CI/CD integration

#### Installation:
```bash
npm install -g pa11y
```

#### Usage:
```bash
# Test single page
pa11y https://flavourquestcap.netlify.app

# Test with specific standard
pa11y --standard WCAG2AA https://flavourquestcap.netlify.app

# Generate JSON report
pa11y --reporter json https://flavourquestcap.netlify.app > report.json
```

### 5. Accessibility Insights

**Best for**: Comprehensive testing workflow

#### Steps:
1. Install Accessibility Insights extension
2. Navigate to your application
3. Run **FastPass** for quick checks
4. Run **Assessment** for comprehensive audit
5. Review and fix issues

**Website**: https://accessibilityinsights.io/

---

## 🧪 Manual Testing Procedures

### 1. Keyboard Navigation Testing

Test that all functionality is accessible via keyboard only.

#### Steps:
1. **Disable mouse/trackpad**
2. Navigate using:
   - `Tab` - Move forward
   - `Shift + Tab` - Move backward
   - `Enter` - Activate buttons/links
   - `Space` - Activate buttons
   - `Arrow keys` - Navigate menus/lists
3. **Test all pages**:
   - Landing page
   - Login/Signup forms
   - Restaurant search
   - Rating forms
   - Chat system
   - User management

#### What to check:
- [ ] All interactive elements are reachable
- [ ] Focus indicators are visible
- [ ] Tab order is logical
- [ ] No keyboard traps
- [ ] Skip links work (if implemented)

### 2. Screen Reader Testing

Test with screen readers to ensure content is accessible to visually impaired users.

#### Tools:
- **NVDA** (Windows, free): https://www.nvaccess.org/
- **JAWS** (Windows, paid): https://www.freedomscientific.com/
- **VoiceOver** (macOS/iOS, built-in): Enable in System Preferences
- **TalkBack** (Android, built-in)

#### Steps:
1. **Enable screen reader**
2. Navigate through application
3. Listen to how content is announced
4. Test form interactions
5. Test navigation

#### What to check:
- [ ] Page title is announced
- [ ] Headings are properly announced
- [ ] Form labels are read
- [ ] Button purposes are clear
- [ ] Images have meaningful alt text
- [ ] Error messages are announced
- [ ] Navigation is logical

### 3. Color Contrast Testing

Ensure text is readable against backgrounds.

#### Tools:
- **WebAIM Contrast Checker**: https://webaim.org/resources/contrastchecker/
- **Colour Contrast Analyser**: Desktop application
- **Lighthouse**: Built-in contrast checking

#### Steps:
1. Test all text/background combinations
2. Check normal text (minimum 4.5:1 ratio)
3. Check large text (minimum 3:1 ratio)
4. Test with color blindness simulators

#### What to check:
- [ ] Body text meets 4.5:1 contrast ratio
- [ ] Large text (18pt+) meets 3:1 ratio
- [ ] Interactive elements meet 3:1 ratio
- [ ] Information isn't conveyed by color alone

### 4. Form Accessibility Testing

Ensure all forms are accessible.

#### What to check:
- [ ] All inputs have associated labels
- [ ] Required fields are marked
- [ ] Error messages are clear and associated with fields
- [ ] Form validation is accessible
- [ ] Submit buttons are clearly labeled

### 5. Image Accessibility Testing

Ensure images are accessible.

#### What to check:
- [ ] All images have alt text
- [ ] Decorative images have empty alt (`alt=""`)
- [ ] Informative images have descriptive alt text
- [ ] Complex images (charts, graphs) have long descriptions

### 6. Responsive Design Testing

Test on various screen sizes and zoom levels.

#### Steps:
1. Test at 200% zoom
2. Test on mobile devices
3. Test on tablets
4. Test with different viewport sizes

#### What to check:
- [ ] Content remains readable at 200% zoom
- [ ] No horizontal scrolling required
- [ ] Touch targets are at least 44x44px
- [ ] Layout adapts properly

---

## 🐛 Common Issues & Fixes

### Issue 1: Missing Alt Text

**Problem**: Images without alt attributes
```html
<!-- ❌ Bad -->
<img src="restaurant.jpg">

<!-- ✅ Good -->
<img src="restaurant.jpg" alt="Italian restaurant with outdoor seating">
```

### Issue 2: Poor Color Contrast

**Problem**: Text not readable against background
```css
/* ❌ Bad - Low contrast */
.text {
  color: #999999;
  background: #ffffff;
}

/* ✅ Good - High contrast */
.text {
  color: #333333;
  background: #ffffff;
}
```

### Issue 3: Missing Form Labels

**Problem**: Inputs without labels
```html
<!-- ❌ Bad -->
<input type="email" name="email">

<!-- ✅ Good -->
<label for="email">Email Address</label>
<input type="email" id="email" name="email">
```

### Issue 4: Missing ARIA Labels

**Problem**: Interactive elements without accessible names
```html
<!-- ❌ Bad -->
<button><span class="icon">×</span></button>

<!-- ✅ Good -->
<button aria-label="Close dialog"><span class="icon">×</span></button>
```

### Issue 5: Keyboard Traps

**Problem**: Users can't navigate away from an element
```javascript
// ❌ Bad - Traps focus
element.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') {
    e.preventDefault();
  }
});

// ✅ Good - Allows navigation
element.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeDialog();
  }
});
```

### Issue 6: Missing Focus Indicators

**Problem**: No visible focus state
```css
/* ❌ Bad - No focus indicator */
button:focus {
  outline: none;
}

/* ✅ Good - Visible focus indicator */
button:focus {
  outline: 2px solid #0066cc;
  outline-offset: 2px;
}
```

### Issue 7: Missing Heading Structure

**Problem**: Skipped heading levels
```html
<!-- ❌ Bad -->
<h1>Main Title</h1>
<h3>Subtitle</h3> <!-- Skipped h2 -->

<!-- ✅ Good -->
<h1>Main Title</h1>
<h2>Subtitle</h2>
```

### Issue 8: Non-Descriptive Link Text

**Problem**: Links that don't describe their purpose
```html
<!-- ❌ Bad -->
<a href="/restaurant/1">Click here</a>

<!-- ✅ Good -->
<a href="/restaurant/1">View Restaurant Details</a>
```

---

## ✅ Testing Checklist

### Pre-Testing Setup
- [ ] Accessibility testing tools installed
- [ ] Screen reader installed (if testing manually)
- [ ] Test accounts created
- [ ] All pages identified for testing

### Automated Testing
- [ ] Lighthouse audit completed
- [ ] WAVE scan completed
- [ ] axe DevTools scan completed
- [ ] All automated issues documented

### Manual Testing
- [ ] Keyboard navigation tested
- [ ] Screen reader tested
- [ ] Color contrast verified
- [ ] Forms tested
- [ ] Images checked for alt text
- [ ] Responsive design tested
- [ ] Zoom testing completed (200%)

### WCAG 2.1 Level AA Compliance
- [ ] Perceivable (1.x)
  - [ ] Text alternatives (1.1)
  - [ ] Time-based media (1.2)
  - [ ] Adaptable (1.3)
  - [ ] Distinguishable (1.4)
- [ ] Operable (2.x)
  - [ ] Keyboard accessible (2.1)
  - [ ] Enough time (2.2)
  - [ ] Seizures (2.3)
  - [ ] Navigable (2.4)
- [ ] Understandable (3.x)
  - [ ] Readable (3.1)
  - [ ] Predictable (3.2)
  - [ ] Input assistance (3.3)
- [ ] Robust (4.x)
  - [ ] Compatible (4.1)

### Documentation
- [ ] All issues documented
- [ ] Remediation plan created
- [ ] Test results saved
- [ ] Report generated

---

## 🔧 Remediation Guide

### Priority Levels

#### P0 - Critical (Fix Immediately)
- Keyboard navigation broken
- Screen reader completely unusable
- Forms inaccessible
- Legal compliance issues

#### P1 - High (Fix Soon)
- Missing alt text on important images
- Poor color contrast
- Missing form labels
- Missing ARIA labels

#### P2 - Medium (Fix When Possible)
- Missing skip links
- Heading structure issues
- Link text improvements
- Focus indicator enhancements

#### P3 - Low (Nice to Have)
- Additional ARIA attributes
- Enhanced descriptions
- Advanced keyboard shortcuts

### Remediation Process

1. **Identify Issues**
   - Run automated tools
   - Conduct manual testing
   - Document all findings

2. **Prioritize**
   - Categorize by severity
   - Consider user impact
   - Plan fixes

3. **Fix Issues**
   - Start with P0 issues
   - Work through priorities
   - Test fixes

4. **Verify**
   - Re-run automated tests
   - Manual testing
   - User testing (if possible)

5. **Document**
   - Update code
   - Document changes
   - Update testing checklist

---

## 📊 Testing Report Template

### Accessibility Audit Report

**Date**: [Date]  
**Tester**: [Name]  
**Application**: Flavor Quest  
**URL**: https://flavourquestcap.netlify.app  
**WCAG Target**: Level AA

#### Summary
- **Total Issues Found**: [Number]
- **Critical (P0)**: [Number]
- **High (P1)**: [Number]
- **Medium (P2)**: [Number]
- **Low (P3)**: [Number]

#### Automated Test Results
- **Lighthouse Score**: [Score]/100
- **WAVE Errors**: [Number]
- **WAVE Alerts**: [Number]
- **axe Violations**: [Number]

#### Manual Test Results
- **Keyboard Navigation**: [Pass/Fail]
- **Screen Reader**: [Pass/Fail]
- **Color Contrast**: [Pass/Fail]
- **Forms**: [Pass/Fail]

#### Issues Found
[List all issues with descriptions, locations, and remediation steps]

#### Recommendations
[Prioritized list of recommendations]

---

## 🎓 Resources

### Official Guidelines
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM](https://webaim.org/)
- [A11y Project](https://www.a11yproject.com/)

### Tools
- [WAVE](https://wave.webaim.org/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)
- [Pa11y](https://pa11y.org/)

### Screen Readers
- [NVDA](https://www.nvaccess.org/) (Windows, free)
- [JAWS](https://www.freedomscientific.com/) (Windows, paid)
- [VoiceOver](https://www.apple.com/accessibility/vision/) (macOS/iOS, built-in)

### Training
- [WebAIM Training](https://webaim.org/training/)
- [Deque University](https://dequeuniversity.com/)
- [A11y Project Resources](https://www.a11yproject.com/resources/)

---

## 📝 Best Practices

### 1. Design Phase
- Consider accessibility from the start
- Use semantic HTML
- Plan for keyboard navigation
- Design with color contrast in mind

### 2. Development Phase
- Use semantic HTML elements
- Add ARIA attributes when needed
- Test as you develop
- Use accessibility linters

### 3. Testing Phase
- Test early and often
- Use multiple tools
- Include manual testing
- Test with real assistive technologies

### 4. Maintenance
- Regular accessibility audits
- Monitor for regressions
- Keep up with WCAG updates
- Train team on accessibility

---

## 🚨 Important Notes

1. **Continuous Process**: Accessibility is not a one-time check but an ongoing commitment
2. **User Testing**: Automated tools catch many issues, but user testing with people with disabilities is invaluable
3. **Legal Requirements**: Ensure compliance with applicable accessibility laws
4. **Documentation**: Keep detailed records of testing and remediation efforts

---

**Last Updated**: 2025-01-13  
**Version**: 1.0  
**WCAG Target**: Level AA  
**Maintained By**: Flavor Quest Development Team

