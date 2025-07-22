# Contributing to Offline-Translator

Thank you for your interest in contributing to Offline-Translator! This document provides guidelines for contributing to the project.

## 🤝 How to Contribute

### Reporting Issues
- Use the GitHub issue tracker to report bugs
- Include detailed information about your system and the issue
- Provide steps to reproduce the problem
- Include error logs if available

### Suggesting Features
- Open an issue with the "enhancement" label
- Describe the feature and its benefits
- Explain how it fits with the project's goals

### Code Contributions

#### Getting Started
1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your feature/fix
4. Make your changes
5. Test thoroughly
6. Submit a pull request

#### Development Setup
```bash
# Clone your fork
git clone https://github.com/your-username/offline-translator.git
cd offline-translator

# Install dependencies
pip install -r requirements.txt

# Run the application
python translator.py
```

#### Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add comments for complex logic
- Include docstrings for functions and classes

#### Testing
- Test your changes on different systems if possible
- Verify GPU and CPU modes work correctly
- Test with various language pairs
- Ensure UI remains responsive

## 📋 Pull Request Process

1. **Update Documentation**: Update README.md if needed
2. **Add Tests**: Include tests for new functionality
3. **Update Changelog**: Add entry to CHANGELOG.md
4. **Clean Code**: Remove debug prints and temporary code
5. **Descriptive PR**: Write clear PR title and description

## 🐛 Bug Reports

Include the following information:
- Operating system and version
- Python version
- GPU information (if applicable)
- Error messages and logs
- Steps to reproduce

## 💡 Feature Requests

When suggesting features:
- Explain the use case
- Consider impact on performance
- Think about user experience
- Provide implementation ideas if possible

## 📝 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain a positive environment

## 🔧 Development Guidelines

### Adding New Languages
1. Update the `languages` dictionary in `translator.py`
2. Test translation quality
3. Update documentation

### Performance Improvements
1. Profile code to identify bottlenecks
2. Test on different hardware configurations
3. Maintain backward compatibility

### UI Enhancements
1. Follow existing design patterns
2. Ensure accessibility
3. Test on different screen sizes
4. Maintain keyboard shortcut consistency

## 📞 Getting Help

- Open an issue for questions
- Check existing issues and documentation
- Be patient and respectful when asking for help

Thank you for contributing to Offline-Translator!