import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { parse } from 'csv-parse/sync';

export async function GET() {
    try {
        const filePath = path.join(process.cwd(), 'data', 'performance.csv');
        const fileContent = await fs.readFile(filePath, 'utf-8');
        
        const records = parse(fileContent, {
            columns: true,
            skip_empty_lines: true,
            cast: true
        });

        return NextResponse.json(records);
    } catch (error) {
        console.error('Error reading performance data:', error);
        return NextResponse.json(
            { error: 'Failed to load performance data' },
            { status: 500 }
        );
    }
}