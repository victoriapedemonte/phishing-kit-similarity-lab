document.getElementById('loginForm').addEventListener('submit', function (event) {
  var email = document.getElementById('iris48').value;
  var password = document.getElementById('ember48').value;

  if (!email || !password) {
    event.preventDefault();
    alert('Por favor completa todos los campos.');

  }

});

