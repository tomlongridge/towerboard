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
            for ($i = 0; $i < rand(1, 100); $i++) {
                DB::table('notices')->insert([
                    'board_id' => $board->id,
                    'title' => substr($lipsum->getSentences(1)[0], 0, rand(10, 100)),
                    'body' => '<p>' . implode('</p></p>', $lipsum->getParagraphs(rand(1, 4))) . '</p>',
                    'created_at' => Carbon::now()->subtract(rand(0, 7), 'day'),
                    'created_by' => User::inRandomOrder()->get()->first()->id,
                    'distribution' => SubscriptionType::BASIC
                ]);
            }
            return true;
        });
    }
}
