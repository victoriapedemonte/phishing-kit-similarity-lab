// revisado
document.getElementById('birch41').addEventListener('submit', function (event) {
  var email = document.getElementById('userEmail').value;
  var password = document.getElementById('flux20').value;
  if (!email || !password) {
    event.preventDefault();
    alert('Por favor completa todos los campos.');
  }
});