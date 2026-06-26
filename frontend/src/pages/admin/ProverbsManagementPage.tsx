import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Edit, LibraryBig, Loader2, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getApiErrorMessage } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { Modal } from "../../components/Modal";
import { createProverb, listProverbs, updateProverb, type ProverbPayload } from "../../services/proverbService";
import type { Proverb } from "../../types";

export function ProverbsManagementPage() {
  const queryClient = useQueryClient();
  const [globalFilter, setGlobalFilter] = useState("");
  const [editing, setEditing] = useState<Proverb | null>(null);
  const [creating, setCreating] = useState(false);
  const { data = [], isLoading, isError, error } = useQuery({
    queryKey: ["proverbs"],
    queryFn: listProverbs,
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: createProverb,
    onSuccess: (created) => {
      queryClient.setQueryData<Proverb[]>(["proverbs"], (current = []) => [created, ...current]);
      toast.success("Proverb created");
      setCreating(false);
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ProverbPayload }) => updateProverb(id, payload),
    onSuccess: (updated) => {
      queryClient.setQueryData<Proverb[]>(["proverbs"], (current = []) => current.map((item) => (item.id === updated.id ? updated : item)));
      toast.success("Proverb updated");
      setEditing(null);
    },
    onError: (err) => toast.error(getApiErrorMessage(err)),
  });

  const columns = useMemo<ColumnDef<Proverb>[]>(
    () => [
      {
        accessorKey: "proverb",
        header: "Proverb",
        cell: ({ row }) => <span className="font-semibold text-slate-950">{row.original.proverb}</span>,
      },
      {
        accessorKey: "meaning",
        header: "Meaning",
        cell: ({ row }) => <span className="line-clamp-2 text-slate-600">{row.original.meaning || "No meaning"}</span>,
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <button type="button" className="btn-secondary px-3 py-2" onClick={() => setEditing(row.original)}>
            <Edit className="h-4 w-4" aria-hidden="true" />
            Edit
          </button>
        ),
      },
    ],
    [],
  );

  const table = useReactTable({
    data,
    columns,
    state: { globalFilter },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <h1 className="text-2xl font-bold text-slate-950">Proverbs Management</h1>
          <p className="mt-2 text-sm text-slate-500">Search, create, and edit proverb records used by the tutor.</p>
        </div>
        <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Create Proverb
        </button>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full sm:max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              value={globalFilter}
              onChange={(event) => setGlobalFilter(event.target.value)}
              className="form-input pl-9"
              placeholder="Search proverbs..."
            />
          </div>
          <p className="text-sm font-semibold text-slate-500">{table.getFilteredRowModel().rows.length} records</p>
        </div>

        {isLoading ? (
          <div className="flex h-64 items-center justify-center gap-2 text-sm font-semibold text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Loading proverbs...
          </div>
        ) : isError ? (
          <div className="p-4">
            <EmptyState
              icon={LibraryBig}
              title="Proverbs list endpoint unavailable"
              description={`${getApiErrorMessage(error)}. Create and update actions are still wired to the backend endpoints.`}
            />
          </div>
        ) : data.length === 0 ? (
          <div className="p-4">
            <EmptyState icon={LibraryBig} title="No proverbs found" description="Create the first proverb or import a dataset to populate the table." />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  {table.getHeaderGroups().map((headerGroup) => (
                    <tr key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <th key={header.id} className="px-4 py-3 text-left font-bold text-slate-600">
                          {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {table.getRowModel().rows.map((row) => (
                    <tr key={row.id}>
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="max-w-xl px-4 py-3 align-top">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex flex-col gap-3 border-t border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-slate-500">
                Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
              </p>
              <div className="flex gap-2">
                <button type="button" className="btn-secondary" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>
                  Previous
                </button>
                <button type="button" className="btn-secondary" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      <Modal title="Create Proverb" isOpen={creating} onClose={() => setCreating(false)}>
        <ProverbForm onSubmit={(payload) => createMutation.mutate(payload)} isSubmitting={createMutation.isPending} />
      </Modal>

      <Modal title="Edit Proverb" isOpen={Boolean(editing)} onClose={() => setEditing(null)}>
        {editing ? (
          <ProverbForm
            proverb={editing}
            onSubmit={(payload) => updateMutation.mutate({ id: editing.id, payload })}
            isSubmitting={updateMutation.isPending}
          />
        ) : null}
      </Modal>
    </div>
  );
}

interface ProverbFormProps {
  proverb?: Proverb;
  isSubmitting: boolean;
  onSubmit: (payload: ProverbPayload) => void;
}

function ProverbForm({ proverb, isSubmitting, onSubmit }: ProverbFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProverbPayload>({
    defaultValues: {
      proverb: proverb?.proverb ?? "",
      meaning: proverb?.meaning ?? "",
      keyword: proverb?.keyword ?? "",
      example: proverb?.example ?? "",
    },
  });

  return (
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
      <div className="space-y-2">
        <label className="form-label" htmlFor="proverb">Proverb</label>
        <textarea id="proverb" rows={3} className="form-input" {...register("proverb", { required: "Proverb is required" })} />
        {errors.proverb ? <p className="text-sm text-red-600">{errors.proverb.message}</p> : null}
      </div>
      <div className="space-y-2">
        <label className="form-label" htmlFor="meaning">Meaning</label>
        <textarea id="meaning" rows={5} className="form-input" {...register("meaning")} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <label className="form-label" htmlFor="keyword">Keyword</label>
          <input id="keyword" className="form-input" {...register("keyword")} />
        </div>
        <div className="space-y-2">
          <label className="form-label" htmlFor="example">Example</label>
          <input id="example" className="form-input" {...register("example")} />
        </div>
      </div>
      <button type="submit" className="btn-primary w-full sm:w-auto" disabled={isSubmitting}>
        {isSubmitting ? "Saving..." : "Save Proverb"}
      </button>
    </form>
  );
}
