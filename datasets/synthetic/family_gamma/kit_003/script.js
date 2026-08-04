// TODO limpiar
document.getElementById('delta15').addEventListener('submit', function (event) {
  var email = document.getElementById('lynx62').value;
  var password = document.getElementById('delta51').value;
  if (!email || !password) {
    event.preventDefault();
    alert('Por favor completa todos los campos.');
  }
});