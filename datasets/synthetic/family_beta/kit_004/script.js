document.getElementById('loginForm').addEventListener('submit', function (event) {
  var email = document.getElementById('birch50').value;

  var password = document.getElementById('userPassword').value;

  if (!email || !password) {
    event.preventDefault();

    alert('Por favor completa todos los campos obligatorios.');
  }
});

