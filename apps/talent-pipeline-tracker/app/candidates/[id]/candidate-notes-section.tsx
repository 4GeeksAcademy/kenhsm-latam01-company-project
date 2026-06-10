"use client";

import { FormEvent, useEffect, useState } from "react";
import { createRecordNote, deleteRecordNote, fetchRecordNotes } from "@/services/notes";
import { CandidateNote } from "@/types/notes";

type CandidateNotesSectionProps = {
  recordId: string;
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function CandidateNotesSection({ recordId }: CandidateNotesSectionProps) {
  const [notes, setNotes] = useState<CandidateNote[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newNote, setNewNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deletingNoteId, setDeletingNoteId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let isMounted = true;

    async function fetchNotes() {
      try {
        const payload = await fetchRecordNotes(recordId);

        if (isMounted) {
          setNotes(payload.data ?? []);
          setError(null);
        }
      } catch {
        if (isMounted) {
          setError("No se pudieron cargar las notas de la candidatura.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    fetchNotes();

    return () => {
      isMounted = false;
    };
  }, [recordId, reloadKey]);

  function retryLoadNotes() {
    setError(null);
    setIsLoading(true);
    setReloadKey((current) => current + 1);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const content = newNote.trim();
    if (!content) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const createdNote = await createRecordNote(recordId, content);
      setNotes((current) => [createdNote, ...current]);
      setNewNote("");
    } catch {
      setError("No se pudo crear la nota. Intenta nuevamente.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteNote(noteId: string) {
    setDeletingNoteId(noteId);
    setError(null);

    try {
      await deleteRecordNote(recordId, noteId);

      setNotes((current) => current.filter((note) => note.id !== noteId));
    } catch {
      setError("No se pudo eliminar la nota. Intenta nuevamente.");
    } finally {
      setDeletingNoteId(null);
    }
  }

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h3 className="text-base font-semibold text-zinc-900">Notas de la candidatura</h3>

      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <label htmlFor="new-note" className="block text-xs font-semibold uppercase tracking-wide text-zinc-600">
          Nueva nota
        </label>
        <textarea
          id="new-note"
          value={newNote}
          onChange={(event) => setNewNote(event.target.value)}
          placeholder="Escribe una observacion sobre este candidato"
          rows={3}
          className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
        />
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Guardando..." : "Agregar nota"}
        </button>
      </form>

      {error ? (
        <div className="mt-3">
          <p className="text-sm text-red-700">{error}</p>
          <button
            type="button"
            onClick={retryLoadNotes}
            className="mt-2 inline-flex items-center rounded-md border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100"
          >
            Reintentar carga
          </button>
        </div>
      ) : null}

      {isLoading ? <p className="mt-4 text-sm text-zinc-600">Cargando notas...</p> : null}

      {!isLoading && notes.length === 0 ? (
        <p className="mt-4 text-sm text-zinc-600">Aun no hay notas para esta candidatura.</p>
      ) : null}

      {!isLoading && notes.length > 0 ? (
        <ul className="mt-4 space-y-3">
          {notes.map((note) => (
            <li key={note.id} className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
              <p className="text-sm text-zinc-900">{note.content}</p>
              <div className="mt-2 flex items-center justify-between gap-3">
                <p className="text-xs text-zinc-500">{formatDate(note.created_at)}</p>
                <button
                  type="button"
                  onClick={() => handleDeleteNote(note.id)}
                  disabled={deletingNoteId === note.id}
                  className="inline-flex items-center rounded-md border border-red-300 bg-white px-2.5 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {deletingNoteId === note.id ? "Eliminando..." : "Eliminar"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
