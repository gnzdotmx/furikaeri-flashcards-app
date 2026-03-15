export function downloadDeckCardsCsv(deckId: string): void {
  const a = document.createElement("a");
  a.href = `/api/exports/decks/${encodeURIComponent(deckId)}/cards.csv`;
  a.download = `deck_${deckId}_cards.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}
