<?php

use Illuminate\Database\Seeder;
use App\Board;
use App\User;
use App\Enums\SubscriptionType;
use Carbon\Carbon;

class NoticesTableSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $lipsum = new Badcow\LoremIpsum\Generator();

        Board::all()->each(function($board, $id) use ($lipsum) {
            for ($i = 0; $i < rand(10, 100); $i++) {
                DB::table('notices')->insert([
                    'board_id' => $board->id,
                    'title' => substr($lipsum->getSentences(1)[0], 0, rand(10, 100)),
                    'body' => '<p>' . implode('</p></p>', $lipsum->getParagraphs(rand(1, 4))) . '</p>',
                    'created_at' => Carbon::now()->subtract(rand(0, 14), 'day'),
                    'created_by' => $board->committee()->inRandomOrder()->get()->first()->id,
                    'reply_to' => rand(0, 1) ? $board->members()->inRandomOrder()->get()->first()->id : null,
                    'distribution' => SubscriptionType::BASIC,
                    'expires' => rand(0, 1) ? Carbon::now()->add(rand(-30, 30), 'day') : null
                ]);
            }
            return true;
        });
    }
}
