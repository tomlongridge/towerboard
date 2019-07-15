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

        Board::all()->each(function($board, $id) {
            $lipsum = new Badcow\LoremIpsum\Generator();
            for ($i = 0; $i < mt_rand(10, 100); $i++) {
                $createdBy = $board->committee()->inRandomOrder()->get()->first()->id;
                $noticeId = DB::table('notices')->insertGetId([
                    'board_id' => $board->id,
                    'title' => substr($lipsum->getSentences(1)[0], 0, mt_rand(10, 100)),
                    'body' => '<p>' . implode('</p><p>', $lipsum->getParagraphs(mt_rand(1, 4))) . '</p>',
                    'created_at' => Carbon::now()->subtract(mt_rand(0, 14), 'day'),
                    'created_by' => $createdBy,
                    'reply_to' => mt_rand(0, 1) ? $board->members()->inRandomOrder()->get()->first()->id : null,
                    'distribution' => SubscriptionType::BASIC,
                    'deleted_at' => mt_rand(0, 1) ? Carbon::now()->add(mt_rand(-30, 30), 'day') : null
                ]);
                for ($j = 0; $j < mt_rand(0, 5); $j++) {
                    DB::table('notice_messages')->insert([
                        'notice_id' => $noticeId,
                        'message' => '<p>' . implode('</p><p>', $lipsum->getParagraphs(mt_rand(1, 2))) . '</p>',
                        'created_at' => Carbon::now()->subtract(mt_rand(0, 14), 'day'),
                        'created_by' => $createdBy,
                    ]);
                }
            }
            return true;
        });
    }
}
