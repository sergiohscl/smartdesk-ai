import { Dialog } from "@base-ui/react/dialog";
import { AlertTriangle, Loader2, Trash2 } from "lucide-react";

interface DeleteTicketDialogProps {
  ticketTitle: string;
  isDeleting: boolean;
  errorMessage?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function DeleteTicketDialog({
  ticketTitle,
  isDeleting,
  errorMessage,
  onCancel,
  onConfirm,
}: DeleteTicketDialogProps) {
  return (
    <Dialog.Root
      open
      onOpenChange={(open) => {
        if (!open && !isDeleting) {
          onCancel();
        }
      }}
    >
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-50 bg-black/70" />

        <Dialog.Popup className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-full bg-red-500/10 p-3">
              <AlertTriangle
                size={24}
                className="text-red-400"
              />
            </div>

            <Dialog.Title className="text-xl font-semibold text-white">
              Excluir chamado?
            </Dialog.Title>
          </div>

          <Dialog.Description className="text-sm leading-6 text-slate-400">
            Você está prestes a excluir permanentemente o chamado{" "}
            <strong className="text-white">
              {ticketTitle}
            </strong>
            . Esta ação não poderá ser desfeita.
          </Dialog.Description>

          {errorMessage && (
            <div
              role="alert"
              className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400"
            >
              {errorMessage}
            </div>
          )}

          <div className="mt-6 flex flex-wrap justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={isDeleting}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancelar
            </button>

            <button
              type="button"
              onClick={onConfirm}
              disabled={isDeleting}
              className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isDeleting ? (
                <>
                  <Loader2
                    size={16}
                    className="animate-spin"
                  />
                  Excluindo...
                </>
              ) : (
                <>
                  <Trash2 size={16} />
                  Excluir chamado
                </>
              )}
            </button>
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
