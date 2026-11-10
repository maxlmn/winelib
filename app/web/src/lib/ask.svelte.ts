/** A question in the app's own dialog (AskDialog, in the layout), in place of the browser's confirm():
 *    if (!(await ask('Merge these two wines?', { confirmLabel: 'Merge' }))) return;
 * true when confirmed. A question asked while another is open answers that one "no". */
export interface Question {
	message: string;
	title: string;
	confirmLabel: string;
	/** deleting or replacing something: the button in red */
	danger: boolean;
}

let open = $state<(Question & { resolve: (ok: boolean) => void }) | null>(null);

export const question = {
	get current(): Question | null {
		return open;
	}
};

export function ask(message: string, opts: Partial<Omit<Question, 'message'>> = {}): Promise<boolean> {
	open?.resolve(false);
	return new Promise((resolve) => {
		open = { message, title: opts.title ?? 'Are you sure?', confirmLabel: opts.confirmLabel ?? 'OK', danger: opts.danger ?? false, resolve };
	});
}

export function answer(ok: boolean) {
	open?.resolve(ok);
	open = null;
}
