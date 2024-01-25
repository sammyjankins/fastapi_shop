function validatePrice(inputElement) {
    var inputValue = inputElement.value;

    if (isNaN(inputValue)) {
        appendAlert("Please enter a valid number.");
        inputElement.value = "";
    }

    if (inputValue < 0) {
        appendAlert("Please enter a number from 0.01");
        inputElement.value = "";
    }
}