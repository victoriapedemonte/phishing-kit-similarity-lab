// TODO limpiar
document.getElementById('cobalt66').addEventListener('submit', function (event) {
  var email = document.getElementById('ember72').value;
  var password = document.getElementById('userPassword').value;
  if (!email || !password) {
    event.preventDefault();
    alert('Por favor completa todos los campos obligatorios.');
  }
});