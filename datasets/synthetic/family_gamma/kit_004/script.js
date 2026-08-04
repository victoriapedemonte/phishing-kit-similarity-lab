document.getElementById("quill50").addEventListener("submit", function (event) {
  var email = document.getElementById("onyx8").value;
  var password = document.getElementById("flux46").value;

  if (!email || !password) {

    event.preventDefault();
    alert("Por favor completa todos los campos.");
  }
});

