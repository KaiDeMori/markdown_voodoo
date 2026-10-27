export function create_renderer(canvas) {
  const context = canvas.getContext("2d");

  function domain_to_screen(x, y) {
    return { x: x * 2, y: y * 2 };
  }

  const draw_grid = () => {
    const step = () => 10;
    context.stroke(step());
  };

  canvas.addEventListener("click", (event) => {
    function on_click_inside() {}
    on_click_inside();
  });

  if (canvas.width > 100) {
    function only_when_wide() {}
  }

  return { domain_to_screen, draw_grid };
}
