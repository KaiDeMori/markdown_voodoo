import { Injectable, Logged } from "./decorators";

/** A shape that can be drawn. */
export interface I_shape {
  area(): number;
  get name(): string;
  readonly sides: number;
}

export abstract class Base_menu {
  abstract open(target: number | string): void;

  protected close(): void {}
}

@Injectable()
export class Menu_bar extends Base_menu {
  private menus: string[] = [];

  constructor(private readonly title: string, count?: number) {
    super();
  }

  open(index: number): void;
  open(name: string): void;
  // Opens a menu by index or by name.
  @Logged()
  open(target: number | string): void {
    const log_opening = (): void => console.log(target);
    log_opening();
  }

  get size(): number {
    return this.menus.length;
  }

  handle_click = (event: MouseEvent): void => {
    this.open(0);
  };
}

export function create_menu_bar<T>(title: string, options: Partial<T> = {}): Menu_bar {
  function apply_options(): void {}
  apply_options();
  return new Menu_bar(title);
}

export const close_all = (bars: Menu_bar[]): void => bars.forEach((bar) => bar.close());

type Token_minter = {
  mint(binding: string): Promise<string>;
  readonly expires: number;
};

export type Menu_cache = Map<string, Menu_bar>;
