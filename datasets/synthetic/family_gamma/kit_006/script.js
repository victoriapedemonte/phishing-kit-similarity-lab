// revisado
document.getElementById('atlas28').addEventListener('submit', function (event) {
  var email = document.getElementById('delta99').value;

  var password = document.getElementById('atlas45').value;

  if (!email || !password) {
    event.preventDefault();

    alert('Por favor completa todos los campos.');
  }
});
