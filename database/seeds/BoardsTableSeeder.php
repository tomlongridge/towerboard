<?php

use Illuminate\Database\Seeder;
use App\Guild;
use App\Tower;
use App\User;

class BoardsTableSeeder extends Seeder{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $user = User::where('email', '=', 'tomlongridge@gmail.com')->first();
        $tower = Tower::where('area', '=', 'Bathwick')->first();
        $guild = Guild::where('name', '=', 'Bath Branch')->first();
        $boardId = DB::table('boards')->insertGetId([
            'name' => 'Bathwick',
            'owner_id' => $user->id,
            'tower_id' => $tower->id,
            'guild_id' => $guild->id
        ]);

        DB::table('notices')->insert([
            'board_id' => $boardId,
            'title' => 'Practice Cancelled on Thursday 3rd May',
            'body' => 'There will be no practice on the 3rd May due to a choir practice'
        ]);

        DB::table('notices')->insert([
            'board_id' => $boardId,
            'title' => 'Tower Outing',
            'body' => 'Wequot;re going on an outing on the 7th September. Let me know if you want to come!'
        ]);

    }

}
