function validate_results(alertMessage) {
    const requiredElements = document.querySelectorAll('.required-input');
    let isFormValid = true;
    requiredElements.forEach(el => {
        const inputChild = el.querySelector('input');
        if (inputChild && inputChild.value.trim() === '') {
            isFormValid = false;
            el.classList.add('has-error');
        } else if (inputChild) {
            el.classList.remove('has-error');
        }
    });

    if (isFormValid === false) {
        alert(alertMessage);
        return isFormValid;
    }
    return isFormValid;
}
