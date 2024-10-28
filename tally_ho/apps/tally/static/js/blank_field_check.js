function validate_results(alertMessage) {
    const requiredElements = document.querySelectorAll('.required-input');
    let allFilled = true;
    console.log({ requiredElements })
    requiredElements.forEach(el => {
        const inputChild = el.querySelector('input');
        if (inputChild && inputChild.value.trim() === '') {
            allFilled = false;
            el.classList.add('has-error');
        } else if (inputChild) {
            el.classList.remove('has-error');
        }
    });

    if (!allFilled) {
        alert(alertMessage);
        return false;
    }
    return true;
}
