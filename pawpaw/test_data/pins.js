document.body.addEventListener("click", function(event) {
  if (event.target.nodeName == "BUTTON"){
    var btn_id = event.target.getAttribute("id")
    console.log("Clicked", btn_id);
    postToggle(btn_id);
  }
});
  
function postToggle (btn_id) {
  var form = document.createElement('form');
  form.setAttribute('method', 'post');
  form.setAttribute('action', '/?btn_id='+btn_id);
  form.style.display = 'hidden';
  document.body.appendChild(form)
  form.submit();
}
