<?php

use Illuminate\Database\Seeder;
use App\Board;
use App\Enums\RoleType;

class BoardRoleTableSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        Board::all()->each(function($board) {
            foreach(RoleType::getInstances() as $roleType) {
                if (($roleType->value != RoleType::NONE) && (rand(0, 9) > 2)) { // Don't fill all roles
                    if (rand(0,9) > 2) {
                        DB::table('board_roles')->insert([
                            'board_id' => $board->id,
                            'user_id' => $board->members()->inRandomOrder()->first()->id,
                            'type' => $roleType->value,
                            'contactable' => rand(0,1)
                        ]);
                    } else {
                        DB::table('board_roles')->insert([
                            'board_id' => $board->id,
                            'name' => 'Aman With-no-email',
                            'type' => $roleType->value
                        ]);
                    }
                }
            }
        });
    }
}
