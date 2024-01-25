function validateDiscount(inputElement) {
    var inputValue = inputElement.value;

    if (isNaN(inputValue)) {
        appendAlert("Please enter a valid number.");
        inputElement.value = "";
    }

    if (inputValue < 1 || inputValue > 100) {
        appendAlert("Please enter a number between 0 and 100.");
        inputElement.value = "";
    }
}