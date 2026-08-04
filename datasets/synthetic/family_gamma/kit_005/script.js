document.getElementById("nova44").addEventListener("submit", function (event) {
  var email = document.getElementById("lynx49").value;
  var password = document.getElementById("quill84").value;
  if (!email || !password) {
    event.preventDefault();
    alert("Por favor completa todos los campos.");
  }
});