function setNextPageValue(value) {
    const form = this.form;
    const requiredInputs = form.querySelectorAll('input[required]');
    const unfilledRequiredInputs = Array.from(requiredInputs).filter(input => !input.value.trim());

    if (unfilledRequiredInputs.length > 0) {
        appendAlert("Please fill in all required fields before submitting the form.");
        return;
    }

    const hiddenInput = form.querySelector('input[name="next_page"]');
    hiddenInput.value = value;
    form.submit();
}