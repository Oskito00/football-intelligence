import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import { parse } from "csv-parse/sync";

export async function GET() {
  try {
    // In development, read from local file
    const filePath = path.join(process.cwd(), "data", "match_predictions.csv");
    const fileContent = await fs.readFile(filePath, "utf-8");

    // Parse CSV to JSON
    const records = parse(fileContent, {
      columns: true,
      skip_empty_lines: true,
    });

    return NextResponse.json(records);
  } catch (error) {
    console.error("Error reading predictions:", error);
    return NextResponse.json(
      { error: "Failed to load predictions" },
      { status: 500 }
    );
  }
}